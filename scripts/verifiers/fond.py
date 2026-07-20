#!/usr/bin/env python3
"""Vérification de FOND des nœuds modifiés par une PR (issue #12) :
re-va chercher chaque chiffre à sa source et compare.

- Ne vérifie que les nœuds AJOUTÉS ou dont le montant a CHANGÉ par rapport
  à une référence git (--base, ex. origin/main) — jamais tout l'arbre.
- Resolvers disponibles (extensibles, un par famille de source) :
    · ods-plf  — nœuds `etat.depenses.*` : re-somme les crédits de paiement
      via l'API data.economie (jeu plf25-depenses-2025-selon-destination) ;
    · ofgl     — nœuds `commune.<insee>.*` dont la source cite un
      « agrégat » OFGL : re-interroge ofgl-base-communes ;
    · pdf      — source en .pdf citant une page : télécharge, extrait la
      page (pdftotext) et vérifie que le montant y figure.
- Détection de doublons : un nœud nouveau qui porte le même (montant,
  annee, producteur) qu'un nœud existant ailleurs.

Verdicts : CONFIRMÉ (la source redonne le chiffre) · ÉCART (elle donne
autre chose → exit 1) · NON VÉRIFIABLE (pas de resolver — information).
Le job CI n'est pas requis par la protection de branche : il informe.

Usage : python3 scripts/verifiers/fond.py --base origin/main [--max 40]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ODS_PLF = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/plf25-depenses-2025-selon-destination/records"
OFGL = "https://data.ofgl.fr/api/explore/v2.1/catalog/datasets/ofgl-base-communes/records"


def api_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ou-va-largent-public/verifier-fond"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:
        # certificats locaux manquants ou réseau : repli curl (fiable en CI et en local)
        r = subprocess.run(["curl", "-fsSL", "--max-time", "30", url], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"API injoignable : {url[:120]}")
        return json.loads(r.stdout)


def arbres(ref=None):
    """Tous les nœuds {id: nœud} de data/ à HEAD (ref=None) ou à une ref git."""
    out = {}
    if ref is None:
        import glob
        fichiers = sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True))
        contenus = [open(f, encoding="utf-8").read() for f in fichiers]
    else:
        ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "data/"],
                            capture_output=True, text=True, cwd=ROOT).stdout.split()
        contenus = [subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True,
                                   text=True, cwd=ROOT).stdout
                    for f in ls if f.endswith(".json")]
    for c in contenus:
        if not c.strip():
            continue
        racine = json.loads(c)
        if "flux" in racine and "poles" in racine:   # document de flux (ADR-0001) :
            for f in racine["flux"]:                  # chaque flux est vérifiable comme un nœud
                out[f["id"]] = f                      # (source complète déclarée, montant, statut)
            continue
        if "segments" in racine and "total_brut_eur" in racine:
            # Dénominateur C·P (ADR-0006) : ce ne sont pas des nœuds de l'arbre mais des
            # agrégats de comptabilité nationale, diffusés en XLSX. Aucun resolver ne sait
            # les re-vérifier automatiquement — ils sont relus à la main en revue de PR.
            continue

        def walk(n, src=None):
            # héritage de source champ par champ (ADR-0005) — même résolution que build.py
            n["source"] = {**(src or {}), **(n.get("source") or {})}
            out[n["id"]] = n
            for k in n.get("enfants", []):
                walk(k, n["source"])

        walk(racine)
    return out


def sans_espaces(s):
    return re.sub(r"[\s   ']", "", s)


# ── Resolvers ────────────────────────────────────────────────────────────────
def resoudre_ods_plf(node):
    """etat.depenses.<TB>.<mission>.<prog>.<action>[.<ss-action>][.tN]"""
    seg = node["id"].split(".")
    if seg[:2] != ["etat", "depenses"] or len(seg) < 3:
        return None
    champs = ["typebudget", "mission", "programme", "action", "sous_action"]
    conds, titre = [], None
    for i, s in enumerate(seg[2:]):
        if re.fullmatch(r"t[1-7]", s):
            titre = s[1]
        elif s.startswith("inconnu"):
            return None
        elif i < len(champs):
            conds.append((champs[i], s))
    if not conds:
        return None
    where = " and ".join(f'{c}="{v}"' for c, v in conds)
    if titre:
        where += f' and titre="{titre}"'
    q = urllib.parse.urlencode({"where": where, "select": "sum(credit_de_paiement)"})
    data = api_json(f"{ODS_PLF}?{q}")
    res = (data.get("results") or [{}])[0]
    val = next(iter(res.values()), None)
    return ("ods-plf", float(val)) if val is not None else None


def resoudre_ofgl(node):
    m = re.match(r"commune\.(\d{5})", node["id"])
    a = re.search(r"agrégat «\s*([^»]+?)\s*»", node["source"].get("nom", ""))
    if not (m and a and node.get("annee")):
        return None
    where = (f'insee="{m.group(1)}" and year(exer)={node["annee"]} '
             f'and type_de_budget="Budget principal" and agregat="{a.group(1)}"')
    q = urllib.parse.urlencode({"where": where, "select": "sum(montant)"})
    data = api_json(f"{OFGL}?{q}")
    res = (data.get("results") or [{}])[0]
    val = next(iter(res.values()), None)
    return ("ofgl", float(val)) if val is not None else None


_PDF_CACHE = {}


def resoudre_pdf(node):
    src = node.get("source", {})
    url = src.get("url", "")
    if ".pdf" not in url.lower():
        return None
    m = re.search(r"p\.\s*(\d+)\s*du PDF", src.get("nom", "")) or re.search(r"p\.\s*(\d+)", src.get("nom", ""))
    if not (m and node.get("montant")):
        return None
    page = int(m.group(1))
    if url not in _PDF_CACHE:
        f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        r = subprocess.run(["curl", "-fsSL", "--max-time", "120", "-o", f.name, url])
        _PDF_CACHE[url] = f.name if r.returncode == 0 else None
    pdf = _PDF_CACHE[url]
    if not pdf:
        raise RuntimeError("PDF intéléchargeable")
    r = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-layout", pdf, "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("pdftotext indisponible ou page invalide")
    texte = sans_espaces(unicodedata.normalize("NFKC", r.stdout))
    # montants en euros dont l'écriture du document est en M€ ou en € :
    candidats = {str(int(node["montant"]))}
    v = abs(node["montant"])
    if v % 1_000_000 == 0:
        candidats.add(str(int(v // 1_000_000)))                  # publié en M€ : 665964
    if v % 100_000_000 == 0:
        candidats.add(f"{v / 1e9:.1f}".replace(".", ","))        # publié en Md€ : 113,7
    trouve = any(c in texte for c in candidats)
    return ("pdf", trouve)


# ── Diff et rapport ──────────────────────────────────────────────────────────
def main():
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "origin/main"
    cap = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 40

    avant, apres = arbres(base), arbres(None)
    # seul un nœud « confirme » prétend être extrait tel quel d'une source —
    # les « estime » (calculs dérivés à méthode humaine) ne sont pas re-vérifiables.
    modifies = [n for i, n in apres.items()
                if n.get("montant") is not None and n.get("statut") == "confirme"
                and (i not in avant or avant[i].get("montant") != n.get("montant"))]
    nouveaux_ids = {n["id"] for n in modifies}

    # doublons : même (montant, annee, producteur) ailleurs dans l'arbre
    doublons = []
    empreintes = {}
    for i, n in apres.items():
        if n.get("montant"):
            empreintes.setdefault((n["montant"], n.get("annee"),
                                   n.get("source", {}).get("producteur")), []).append(i)
    def meme_lignee(a, b):  # parent/enfant/ancêtre : même montant légitime
        return a.startswith(b + ".") or b.startswith(a + ".")

    for n in modifies:
        cle = (n["montant"], n.get("annee"), n.get("source", {}).get("producteur"))
        lies = set(n.get("noeuds_lies", []))   # un flux porte légitimement le montant de son nœud lié
        freres = [i for i in empreintes.get(cle, [])
                  if i != n["id"] and i not in nouveaux_ids and i not in lies and not meme_lignee(i, n["id"])]
        if freres:
            doublons.append(f"{n['id']} porte le même (montant, année, producteur) que {freres[0]}")

    echantillon = modifies[:cap]
    confirmes, ecarts, non_verif = [], [], []
    for n in echantillon:
        try:
            res = resoudre_ods_plf(n) or resoudre_ofgl(n) or resoudre_pdf(n)
        except Exception as e:  # noqa: BLE001 — un resolver qui casse ≠ un écart
            non_verif.append(f"{n['id']} (erreur resolver : {e})")
            continue
        if res is None:
            non_verif.append(n["id"])
        elif res[0] == "pdf":
            (confirmes if res[1] else ecarts).append(
                f"{n['id']} : montant {'retrouvé' if res[1] else 'INTROUVABLE'} sur la page citée du PDF")
        else:
            attendu, obtenu = float(n["montant"]), res[1]
            if abs(obtenu - attendu) < 0.01:
                confirmes.append(f"{n['id']} : {obtenu:,.2f} € ({res[0]})")
            else:
                ecarts.append(f"{n['id']} : PR = {attendu:,.2f} € mais {res[0]} = {obtenu:,.2f} €")

    lignes = [f"nœuds modifiés vs {base} : {len(modifies)}"
              + (f" (vérification plafonnée aux {cap} premiers — le reste relève d'un pipeline)" if len(modifies) > cap else "")]
    if doublons:
        lignes += ["⚠ DOUBLONS possibles :"] + [f"  ⚠ {d}" for d in doublons]
    if confirmes:
        lignes += [f"✅ CONFIRMÉS À LA SOURCE : {len(confirmes)}"] + [f"  ✓ {c}" for c in confirmes]
    if ecarts:
        lignes += [f"❌ ÉCARTS : {len(ecarts)}"] + [f"  ✗ {e}" for e in ecarts]
    if non_verif:
        lignes += [f"ℹ non vérifiables automatiquement : {len(non_verif)}"] + [f"  · {v}" for v in non_verif[:15]]
    if not modifies:
        lignes.append("aucun montant modifié — rien à vérifier")
    print("\n".join(lignes))

    resume = os.environ.get("GITHUB_STEP_SUMMARY")
    if resume:
        with open(resume, "a", encoding="utf-8") as fh:
            fh.write("### Vérification de fond des sources\n\n```\n" + "\n".join(lignes) + "\n```\n")

    sys.exit(1 if ecarts else 0)


if __name__ == "__main__":
    main()
