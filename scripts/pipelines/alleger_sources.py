#!/usr/bin/env python3
"""Allège les fichiers data/ en appliquant l'héritage de source (ADR-0005) :
retire de chaque nœud tout champ de `source` égal au champ RÉSOLU de son
parent ; si la source devient vide, retire le champ entier. La racine de
chaque fichier garde sa source complète (ancre de l'héritage).

Migration sans perte par construction : build.py résout l'héritage à la
génération — les fichiers générés (data.js, couverture, fragments) doivent
être IDENTIQUES octet pour octet avant/après. Rejouable : un second passage
ne change plus rien.

Usage : python3 scripts/pipelines/alleger_sources.py
Puis  : python3 scripts/build.py   (et comparer les générés — critère d'or)
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDRE = ("nom", "url", "producteur", "licence", "consulte_le", "maj", "archive")


def alleger(node, parent_resolue=None):
    declaree = node.get("source") or {}
    resolue = {**(parent_resolue or {}), **declaree}
    if parent_resolue is not None and "source" in node:  # jamais la racine (ancre) ; rien à faire si déjà tout hérité
        restee = {k: v for k, v in declaree.items() if parent_resolue.get(k, "\0absent") != v}
        restee = {k: restee[k] for k in ORDRE if k in restee} | {
            k: v for k, v in restee.items() if k not in ORDRE}
        if restee:
            node["source"] = restee
        else:
            # Retrait total seulement si la clé précède immédiatement « enfants » —
            # la résolution la réinsérera exactement là. Sinon, {} (= tout hérité)
            # préserve la position d'origine (critère d'or : générés identiques).
            cles = list(node.keys())
            i = cles.index("source")
            if i + 1 < len(cles) and cles[i + 1] == "enfants":
                node.pop("source")
            else:
                node["source"] = {}
    for c in node.get("enfants", []):
        alleger(c, resolue)


def main():
    total_avant = total_apres = fichiers = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True)):
        avant = os.path.getsize(f)
        with open(f, encoding="utf-8") as fh:
            tree = json.load(fh)
        alleger(tree)
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(tree, fh, ensure_ascii=False, indent=1)
        total_avant += avant
        total_apres += os.path.getsize(f)
        fichiers += 1
    gain = (1 - total_apres / total_avant) * 100 if total_avant else 0
    print(f"{fichiers} fichiers : {total_avant/1e6:.2f} Mo → {total_apres/1e6:.2f} Mo (−{gain:.1f} %)")


if __name__ == "__main__":
    main()
