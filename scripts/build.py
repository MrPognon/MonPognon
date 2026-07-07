#!/usr/bin/env python3
"""Valide les fichiers data/ et génère site/data.js.
Usage : python3 scripts/build.py [--check]        validation seule, pour la CI
        python3 scripts/build.py --show <id>      affiche un nœud, source résolue (ADR-0005)"""
import json, sys, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUTS = {"confirme", "estime", "inconnu"}
errors, warnings = [], []

def resoudre_sources(node, path, parent_src=None):
    """Héritage de la source champ par champ, en descendant (ADR-0005).
    Un nœud sans source hérite tout ; une source partielle hérite des champs
    manquants ; la racine du fichier doit être complète (ancre). Après cette
    passe, chaque nœud porte sa source résolue — c'est elle qui est validée,
    générée dans data.js et les fragments, et affichée sur le site."""
    declaree = node.get("source")
    if parent_src is None and not declaree:
        errors.append(f"{path}: la racine du fichier doit porter une source complète — ancre de l'héritage ({node.get('id','?')})")
        return
    resolue = {**(parent_src or {}), **(declaree or {})}
    if "source" in node:
        node["source"] = resolue          # la clé garde sa position d'origine
    else:                                  # clé absente : l'insérer AVANT 'enfants'
        cles = list(node.keys())
        node["source"] = resolue
        if "enfants" in cles:
            for k in cles[cles.index("enfants"):]:
                node[k] = node.pop(k)      # repousse enfants (et la suite) après source
    for c in node.get("enfants", []):
        resoudre_sources(c, path, node["source"])

def validate(node, path, seen_ids):
    for req in ("id", "label", "statut", "source", "enfants"):
        if req not in node:
            errors.append(f"{path}: champ requis manquant '{req}' (nœud {node.get('id','?')})"); return
    if node["id"] in seen_ids: errors.append(f"{path}: id dupliqué {node['id']}")
    seen_ids.add(node["id"])
    if node["statut"] not in STATUTS: errors.append(f"{path}: statut invalide '{node['statut']}' ({node['id']})")
    if node["statut"] == "inconnu" and "inconnu" not in node:
        errors.append(f"{path}: statut 'inconnu' sans bloc 'inconnu' (qui contacter ?) ({node['id']})")
    src = node["source"]
    for req in ("nom", "url", "producteur", "consulte_le"):
        if not src.get(req): errors.append(f"{path}: source.{req} manquant ({node['id']})")
    maj = src.get("maj")
    if maj is not None and not (isinstance(maj, str) and len(maj) == 10 and maj[4] == "-" and maj[7] == "-"):
        errors.append(f"{path}: source.maj doit être au format AAAA-MM-JJ ou null ({node['id']})")
    if node.get("montant") is not None and maj is None:
        warnings.append(f"{path}: montant sans date de mise à jour de la source (source.maj) ({node['id']})")
    m = node.get("montant")
    if m is not None and not isinstance(m, (int, float)): errors.append(f"{path}: montant non numérique ({node['id']})")
    if m is not None and node.get("annee") is None: warnings.append(f"{path}: montant sans année ({node['id']})")
    kids = [c for c in node["enfants"] if c.get("montant")]
    if m and kids:
        s = sum(c["montant"] for c in kids)
        if s > m * 1.02:
            warnings.append(f"{path}: somme des enfants ({s:,.0f}) > parent ({m:,.0f}) de plus de 2 % ({node['id']})")
    for c in node["enfants"]: validate(c, path, seen_ids)

METHODE_COUVERTURE = (
    "Chaque euro du montant racine d'un arbre est attribué au statut du nœud le plus profond qui le porte : "
    "un total confirmé dont la ventilation fine est estimée compte comme estimé — le baromètre mesure la "
    "profondeur réelle du sourçage, pas la surface. Allocation descendante : les enfants à montant positif "
    "reçoivent leur montant (au pro-rata si leur somme dépasse le parent, cas des transferts internes) ; le "
    "reliquat non détaillé reste porté par le parent. Les montants négatifs (nœuds de neutralisation) sont "
    "exclus de l'allocation. Les arbres ne sont JAMAIS additionnés entre eux (transferts inter-administrations : "
    "TVA affectée, dotations…) — chaque périmètre se lit seul."
)


def couverture(node):
    """Répartition du montant racine par statut / millésime / profondeur du porteur (cf. METHODE_COUVERTURE)."""
    acc = {"statuts": {"confirme": 0.0, "estime": 0.0, "inconnu": 0.0},
           "annees": {}, "profondeurs": {}, "maj_renseignee": 0.0}

    def poser(n, euros, prof):
        if euros <= 0:
            return
        acc["statuts"][n["statut"]] += euros
        a = str(n.get("annee") or "?")
        acc["annees"][a] = acc["annees"].get(a, 0.0) + euros
        acc["profondeurs"][str(prof)] = acc["profondeurs"].get(str(prof), 0.0) + euros
        if n.get("source", {}).get("maj"):
            acc["maj_renseignee"] += euros

    def repartir(n, alloue, prof):
        kids = [c for c in n["enfants"] if isinstance(c.get("montant"), (int, float)) and c["montant"] > 0]
        total = sum(c["montant"] for c in kids)
        if not kids or alloue <= 0:
            poser(n, alloue, prof)
            return
        if total >= alloue:  # dépassement (transferts internes) : pro-rata
            for c in kids:
                repartir(c, alloue * c["montant"] / total, prof + 1)
        else:                # ventilation partielle : le reliquat reste au parent
            for c in kids:
                repartir(c, c["montant"], prof + 1)
            poser(n, alloue - total, prof)

    repartir(node, node.get("montant") or 0, 0)
    noeuds, inconnues, demandes = {"confirme": 0, "estime": 0, "inconnu": 0}, 0, 0

    def compter(n):
        nonlocal inconnues, demandes
        noeuds[n["statut"]] += 1
        if n["statut"] == "inconnu":
            inconnues += 1
            if (n.get("inconnu") or {}).get("url"):
                demandes += 1
        for c in n["enfants"]:
            compter(c)

    compter(node)
    m = node.get("montant") or 0
    return {
        "label": node["label"], "montant": m,
        "statuts": {k: round(v, 2) for k, v in acc["statuts"].items()},
        "pct_confirme": round(acc["statuts"]["confirme"] / m * 100, 1) if m else None,
        "annees": {k: round(v, 2) for k, v in sorted(acc["annees"].items())},
        "profondeurs": {k: round(v, 2) for k, v in sorted(acc["profondeurs"].items())},
        "maj_renseignee_pct": round(acc["maj_renseignee"] / m * 100, 1) if m else None,
        "noeuds": noeuds,
        "inconnues": {"total": inconnues, "avec_demande": demandes},
    }


def maj_readme(cov):
    """Régénère le tableau de couverture du README entre ses balises (si présentes)."""
    debut, fin = "<!-- couverture:debut -->", "<!-- couverture:fin -->"
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as fh:
        texte = fh.read()
    if debut not in texte or fin not in texte:
        return False
    md = lambda v: f"{v / 1e9:,.1f}".replace(",", " ").replace(".", ",") + " Md€"
    lignes = ["| Périmètre | Montant | ✅ confirmé (en €) | 🟡 estimé | ❓ à réclamer |", "|---|---|---|---|---|"]
    for cle, c in cov.items():
        s, m = c["statuts"], c["montant"]
        pc = lambda v: f"{v / m * 100:,.1f}".replace(".", ",") + " %" if m else "—"
        lignes.append(f"| {c['label']} | {md(m)} | **{pc(s['confirme'])}** | {pc(s['estime'])} | "
                      f"{c['inconnues']['total']} nœud(s), dont {c['inconnues']['avec_demande']} réclamé(s) |")
    lignes.append("")
    lignes.append("*Un euro est « confirmé » si le nœud le plus profond qui le porte l'est — la méthode complète "
                  "est dans [`site/couverture.json`](site/couverture.json). Les périmètres ne s'additionnent pas "
                  "(transferts entre administrations). Tableau régénéré par `build.py`.*")
    bloc = debut + "\n" + "\n".join(lignes) + "\n" + fin
    nouveau = texte[: texte.index(debut)] + bloc + texte[texte.index(fin) + len(fin):]
    if nouveau != texte:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(nouveau)
    return True


def main():
    data, fiches, seen = {}, {}, set()
    communes_dir = os.path.join(ROOT, "data", "collectivites", "communes") + os.sep
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True)):
        key = os.path.relpath(f, os.path.join(ROOT, "data")).replace(os.sep, "_").removesuffix(".json")
        with open(f, encoding="utf-8") as fh:
            node = json.load(fh)
        resoudre_sources(node, os.path.relpath(f, ROOT))
        validate(node, os.path.relpath(f, ROOT), seen)
        # Fiches communales (ADR-0004) : validées comme le reste, publiées en
        # fragments individuels chargés à la demande — jamais dans data.js.
        if f.startswith(communes_dir):
            fiches[os.path.basename(f).removesuffix(".json")] = node
        else:
            data[key] = node
    if "--show" in sys.argv:  # affiche un nœud avec sa source résolue (ADR-0005)
        cible = sys.argv[sys.argv.index("--show") + 1]
        def chercher(n):
            if n["id"] == cible: return n
            return next((r for c in n.get("enfants", []) if (r := chercher(c))), None)
        for arbre in list(data.values()) + list(fiches.values()):
            n = chercher(arbre)
            if n:
                apercu = {k: v for k, v in n.items() if k != "enfants"}
                apercu["enfants"] = f"[{len(n.get('enfants', []))} enfant(s)]"
                print(json.dumps(apercu, ensure_ascii=False, indent=1)); return
        print(f"id introuvable : {cible}", file=sys.stderr); sys.exit(1)
    for w in warnings: print("AVERTISSEMENT:", w)
    if errors:
        for e in errors: print("ERREUR:", e, file=sys.stderr)
        sys.exit(1)
    extra = f" + {len(fiches)} fiche(s) communale(s)" if fiches else ""
    print(f"OK — {len(data)} fichiers{extra}, {len(seen)} nœuds validés")
    if "--check" not in sys.argv:
        out = os.path.join(ROOT, "site", "data.js")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/)\n")
            fh.write("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
        print("→", out)
        if fiches:
            frag_dir = os.path.join(ROOT, "site", "data", "communes")
            os.makedirs(frag_dir, exist_ok=True)
            for insee, node in sorted(fiches.items()):
                with open(os.path.join(frag_dir, insee + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(node, fh, ensure_ascii=False)
            print(f"→ {frag_dir}{os.sep} ({len(fiches)} fragment(s))")
        # Baromètre de couverture (issue #15) — par arbre, jamais sommé entre arbres.
        cov = {k: couverture(n) for k, n in data.items()}
        cov_doc = {"methode": METHODE_COUVERTURE, "arbres": cov}
        with open(os.path.join(ROOT, "site", "couverture.json"), "w", encoding="utf-8") as fh:
            json.dump(cov_doc, fh, ensure_ascii=False, indent=1)
        with open(os.path.join(ROOT, "site", "couverture.js"), "w", encoding="utf-8") as fh:
            fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/)\n")
            fh.write("window.COUVERTURE = " + json.dumps(cov_doc, ensure_ascii=False) + ";\n")
        readme_ok = maj_readme(cov)
        print(f"→ site/couverture.json + couverture.js{' + README (tableau)' if readme_ok else ''}")

if __name__ == "__main__": main()
