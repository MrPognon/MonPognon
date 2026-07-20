#!/usr/bin/env python3
"""Vérifie la confiance des URLs de sources de data/ (issue #13).

Deux familles de contrôles :
- HYGIÈNE (violations dures → exit 1) : HTTPS obligatoire, pas d'adresse IP,
  pas de raccourcisseur d'URL, pas de punycode (xn--), pas de domaine à
  distance d'édition ≤ 2 d'un domaine officiel (typosquat probable).
- CONFIANCE (informatif) : classement de chaque domaine par tier —
  1 = officiel national (data-sources/domaines/tier1.txt, matching par suffixe),
  3 = approuvé par les mainteneurs (data-sources/domaines/approuves.json),
  4 = inconnu → revue humaine ciblée (label « domaine-a-verifier » côté CI).
  (Le tier 2 — sites officiels des collectivités vérifiés via l'Annuaire de
  l'administration — sera ajouté avec le référentiel DILA, voir issue #13.)

Par défaut : contrôles statiques uniquement (déterministe, pour la CI).
--online ajoute la vérification que chaque URL répond (HTTP < 400) sans
rediriger vers un autre domaine enregistrable.

Usage : python3 scripts/verifier_sources.py [--online] [--data DIR]
Sortie : rapport texte + markdown dans $GITHUB_STEP_SUMMARY si défini.
"""
import glob
import ipaddress
import json
import os
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOM_DIR = os.path.join(ROOT, "data-sources", "domaines")

# Les documents versionnés dans CE dépôt (data-sources/documents/, politique #14) sont
# des sources légitimes : revus en PR, provenance obligatoire. Le préfixe est exact —
# github.com en général resterait un domaine inconnu (n'importe qui peut y publier).
PREFIXE_DEPOT = "https://github.com/MrPognon/MonPognon/blob/main/data-sources/documents/"

RACCOURCISSEURS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "cutt.ly", "rebrand.ly", "shorturl.at", "urlr.me", "lstu.fr", "frama.link",
}


def domaine_enregistrable(netloc):
    """Approximation eTLD+1 : les deux derniers labels (suffisant pour .fr)."""
    labels = netloc.lower().rstrip(".").split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else netloc.lower()


def levenshtein(a, b):
    if abs(len(a) - len(b)) > 2:
        return 3  # borne suffisante pour notre seuil
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def charger_tiers():
    tier1 = []
    with open(os.path.join(DOM_DIR, "tier1.txt"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                tier1.append(line.lower())
    with open(os.path.join(DOM_DIR, "approuves.json"), encoding="utf-8") as fh:
        tier3 = [d["domaine"].lower() for d in json.load(fh)["domaines"]]
    return tier1, tier3


def matche(netloc, entree):
    return netloc == entree or netloc.endswith("." + entree)


def collecter_urls(data_dir):
    """Toutes les URLs de data/ avec les ids des nœuds qui les portent."""
    urls = {}
    for f in sorted(glob.glob(os.path.join(data_dir, "**", "*.json"), recursive=True)):
        with open(f, encoding="utf-8") as fh:
            tree = json.load(fh)

        # Dénominateurs C·P (ADR-0006) : pas un arbre de nœuds, mais leurs sources
        # doivent passer les mêmes contrôles d'hygiène et de tiers de confiance.
        if isinstance(tree, dict) and "segments" in tree and "total_brut_eur" in tree:
            def walk_denom(o, etiquette):
                if isinstance(o, dict):
                    etiquette = o.get("code") or o.get("nom") or etiquette
                    u = o.get("url")
                    if isinstance(u, str) and u.startswith("http"):
                        urls.setdefault(u, []).append(etiquette)
                    for v in o.values():
                        walk_denom(v, etiquette)
                elif isinstance(o, list):
                    for v in o:
                        walk_denom(v, etiquette)

            walk_denom(tree, os.path.basename(f))
            continue

        def walk(n):
            for champ in ("source", "inconnu", "a_completer"):
                u = (n.get(champ) or {}).get("url")
                if u:
                    urls.setdefault(u, []).append(n["id"])
            for c in n.get("enfants", []):
                walk(c)

        walk(tree)
    return urls


def verifier(urls, tier1, tier3):
    violations, tiers = [], {}
    for u, ids in urls.items():
        p = urlparse(u)
        netloc = (p.hostname or "").lower()
        exemple = f"{u} (ex. {ids[0]})"
        if p.scheme != "https":
            violations.append(f"HTTPS obligatoire : {exemple}")
            continue
        try:
            ipaddress.ip_address(netloc)
            violations.append(f"adresse IP interdite : {exemple}")
            continue
        except ValueError:
            pass
        if "xn--" in netloc:
            violations.append(f"punycode interdit (homoglyphes possibles) : {exemple}")
            continue
        reg = domaine_enregistrable(netloc)
        if reg in RACCOURCISSEURS:
            violations.append(f"raccourcisseur d'URL interdit : {exemple}")
            continue
        if u.startswith(PREFIXE_DEPOT):
            tiers.setdefault("depot", set()).add("(documents versionnés du dépôt)")
            continue
        if any(matche(netloc, t) for t in tier1):
            tiers.setdefault(1, set()).add(netloc)
            continue
        if any(matche(netloc, t) for t in tier3):
            tiers.setdefault(3, set()).add(netloc)
            continue
        # typosquat : domaine proche d'un officiel sans en être un
        proche = next((t for t in tier1 if levenshtein(reg, t) <= 2 and reg != t), None)
        if proche:
            violations.append(f"ressemble à « {proche} » (typosquat probable) : {exemple}")
            continue
        tiers.setdefault(4, set()).add(netloc)
    return violations, tiers


def verifier_en_ligne(urls):
    """Via curl (certificats système fiables partout, contrairement à urllib)."""
    import subprocess

    problemes = []
    for u in sorted(urls):
        r = subprocess.run(
            ["curl", "-sSL", "-o", "/dev/null", "--max-time", "25",
             "-A", "ou-va-largent-public/verifier-sources",
             "-w", "%{http_code} %{url_effective}", u],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            problemes.append(f"injoignable ({r.stderr.strip().splitlines()[-1][:80] if r.stderr else 'curl ' + str(r.returncode)}) : {u}")
            continue
        code, _, finale = r.stdout.strip().partition(" ")
        if not code.isdigit() or int(code) >= 400:
            problemes.append(f"HTTP {code} : {u}")
            continue
        origine = domaine_enregistrable(urlparse(u).hostname or "")
        arrivee = domaine_enregistrable(urlparse(finale).hostname or "")
        if arrivee and arrivee != origine:
            problemes.append(f"redirige hors domaine ({origine} → {arrivee}) : {u}")
    return problemes


def main():
    data_dir = os.path.join(ROOT, "data")
    if "--data" in sys.argv:
        data_dir = sys.argv[sys.argv.index("--data") + 1]
    tier1, tier3 = charger_tiers()
    urls = collecter_urls(data_dir)
    violations, tiers = verifier(urls, tier1, tier3)

    lignes = [f"URLs distinctes : {len(urls)}"]
    for t, label in ((1, "tier 1 · officiel national"), ("depot", "dépôt · document versionné, revu en PR"), (3, "tier 3 · approuvé"), (4, "tier 4 · INCONNU — revue humaine")):
        for d in sorted(tiers.get(t, ())):
            lignes.append(f"  [{label}] {d}")
    if violations:
        lignes.append("VIOLATIONS (bloquantes) :")
        lignes += [f"  ✗ {v}" for v in violations]
    inconnus = tiers.get(4, set())
    if inconnus:
        lignes.append(f"⚠ {len(inconnus)} domaine(s) inconnu(s) : à justifier dans la PR, "
                      f"un mainteneur peut les ajouter à data-sources/domaines/approuves.json")
    ok_msg = "✅ hygiène des sources : OK" if not violations else "❌ hygiène des sources : violations"
    lignes.append(ok_msg)
    print("\n".join(lignes))

    if "--online" in sys.argv:
        problemes = verifier_en_ligne(urls)
        if problemes:
            print("Vérification en ligne (informatif) :")
            for pb in problemes:
                print(f"  ⚠ {pb}")
        else:
            print("✅ toutes les URLs répondent sans redirection hors domaine")

    resume = os.environ.get("GITHUB_STEP_SUMMARY")
    if resume:
        with open(resume, "a", encoding="utf-8") as fh:
            fh.write("### Confiance des sources\n\n```\n" + "\n".join(lignes) + "\n```\n")

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
