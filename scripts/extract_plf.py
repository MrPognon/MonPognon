#!/usr/bin/env python3
"""Exemple d'extraction depuis l'API data.economie.gouv.fr (Opendatasoft Explore v2.1).
Sert de modèle pour intégrer le détail programmes → actions des 33 missions restantes.
Les parenthèses et quotes DOIVENT être URL-encodées."""
import json, urllib.request, urllib.parse

BASE = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/plf25-depenses-2025-selon-destination/records"

def get(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.load(r)["results"]

if __name__ == "__main__":
    mission = "Défense"  # exemple : changez la mission à intégrer
    rows = get({
        "select": "sum(credit_de_paiement) as cp",
        "group_by": "programme,libelle_programme,action,libelle_action",
        "where": f"libelle_mission='{mission}'",
        "limit": "100",
    })
    print(json.dumps(rows, ensure_ascii=False, indent=1))
