#!/usr/bin/env python3
"""Ventile chaque feuille de l'arbre des dépenses de l'État (sous-action, ou
action sans sous-action) par nature de dépense — les titres budgétaires de la
LOLF (art. 5) — à partir de l'extrait brut déjà téléchargé
data-sources/raw/depenses-full.json (jeu plf25-depenses-2025-selon-destination,
granularité sous-action × catégorie × titre). Zéro appel réseau.

Pipeline rejouable (ADR-0002) : chaque exécution régénère les enfants de titre
(.t1 à .t7) des feuilles — relancer le script produit un diff vide.

La ventilation n'est injectée QUE si la somme des titres réconcilie le montant
de la feuille au centime ; sinon la feuille est laissée intacte et listée.

Usage : python3 scripts/pipelines/ventiler_par_nature.py
Puis  : python3 scripts/build.py   (validation + régénération de site/data.js)
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data-sources", "raw", "depenses-full.json")
DATA = os.path.join(ROOT, "data", "etat", "depenses.json")

# Les 7 titres de l'article 5 de la LOLF (loi organique n° 2001-692).
TITRES = {
    "1": "Dotations des pouvoirs publics",
    "2": "Dépenses de personnel",
    "3": "Dépenses de fonctionnement",
    "4": "Charges de la dette de l'État",
    "5": "Dépenses d'investissement",
    "6": "Dépenses d'intervention",
    "7": "Dépenses d'opérations financières",
}
TITRE_ID = re.compile(r"\.t[1-7]$")


def entier_si_possible(v):
    return int(v) if float(v).is_integer() else round(v, 2)


def main():
    with open(RAW, encoding="utf-8") as fh:
        rows = json.load(fh)
    with open(DATA, encoding="utf-8") as fh:
        tree = json.load(fh)

    # 1. Agréger les crédits de paiement par (code feuille, titre).
    #    Le code feuille = la sous-action quand elle existe, sinon l'action.
    agg = {}
    for r in rows:
        code = r["sous_action"] or r["action"]
        agg.setdefault(code, {})[r["titre"]] = (
            agg.get(code, {}).get(r["titre"], 0) + (r["credit_de_paiement"] or 0)
        )

    # 2. Injecter la ventilation sous chaque feuille correspondante.
    stats = {"ventilees": 0, "noeuds": 0, "intactes": []}

    def walk(n):
        kids = n.get("enfants", [])
        est_feuille = not kids or all(TITRE_ID.search(c["id"]) for c in kids)
        code = n["id"].split(".")[-1]
        if est_feuille and code in agg:
            titres = agg[code]
            somme = sum(titres.values())
            montant = n.get("montant") or 0
            if abs(somme - montant) >= 0.01:  # jamais de ventilation qui ne réconcilie pas
                stats["intactes"].append((n["id"], montant, somme))
                return
            n["enfants"] = [
                {
                    "id": f"{n['id']}.t{t}",
                    "label": f"Titre {t} — {TITRES[t]}",
                    "montant": entier_si_possible(v),
                    "annee": n.get("annee"),
                    "statut": "confirme",
                    "source": dict(n["source"]),
                    "enfants": [],
                }
                for t, v in sorted(titres.items())
            ]
            stats["ventilees"] += 1
            stats["noeuds"] += len(n["enfants"])
            return
        for c in kids:
            walk(c)

    walk(tree)

    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump(tree, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print(f"feuilles ventilées : {stats['ventilees']}")
    print(f"nœuds de titre     : {stats['noeuds']}")
    if stats["intactes"]:
        print(f"feuilles NON ventilées (écart de réconciliation) : {len(stats['intactes'])}")
        for i, m, s in stats["intactes"]:
            print(f"  ⚠ {i}: feuille {m:,.2f} vs titres {s:,.2f}")
        sys.exit(1)
    print("réconciliation : exacte au centime sur toutes les feuilles ventilées ✅")


if __name__ == "__main__":
    main()
