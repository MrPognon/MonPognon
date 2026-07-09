#!/usr/bin/env python3
"""Génère la vue transverse « Qui paie ? » (issue #5) : data/etat/qui-paie.json.

Première sous-vue : L'IMPÔT SUR LE REVENU PAR TRANCHE DE REVENU FISCAL DE
RÉFÉRENCE — fichier national de l'IRCOM (DGFiP), revenus 2024 émis en 2025.
Chaque tranche porte l'impôt net émis (négatif pour les tranches basses :
restitutions), le nombre de foyers et leur revenu fiscal total ; les
sous-tranches au-delà de 100 000 € sont détaillées jusqu'à « plus de 9 M€ ».

La racine de la vue porte un montant null : ces montants (émission par voie
de rôle, millésime propre) ne s'additionnent pas aux lignes prévisionnelles
de l'état A — vue transverse, jamais sommée (même pattern que « Qui perçoit ? »).

Rejouable : lit l'extrait versionné data-sources/raw/ircom-2025-national.json
(cellules du fichier officiel, montants en milliers d'euros — extraction
documentée dans le .meta.json). Zéro appel réseau, zéro dépendance.
Usage : python3 scripts/pipelines/qui_paie.py && python3 scripts/build.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRINCIPALES = ["0 à 10 000", "10 001 à 12 000", "12 001 à 15 000", "15 001 à 20 000",
               "20 001 à 30 000", "30 001 à 50 000", "50 001 à 100 000", "Plus de 100 000 dont:"]


def fr(n):
    return f"{n:,.0f}".replace(",", " ")


def main():
    raw = json.load(open(os.path.join(ROOT, "data-sources", "raw", "ircom-2025-national.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(ROOT, "data-sources", "raw", "ircom-2025-national.meta.json"), encoding="utf-8"))
    src = {"nom": "DGFiP — IRCOM, fichier national (revenus 2024 déclarés en 2025), tableau par tranche de RFR ; montants en milliers d'euros",
           "url": meta["source_page"], "producteur": "DGFiP",
           "licence": "Licence Ouverte 2.0", "consulte_le": meta["consulte_le"], "maj": meta["maj_dataset"]}

    def slugt(label):
        s = re.sub(r"[^0-9a-z]+", "-", label.lower().replace("à", "a")).strip("-")
        return s or "t"

    def noeud_tranche(t, prefixe, enfants=None):
        negatif = t["impot_net_milliers"] < 0
        desc = (f"{fr(t['foyers'])} foyers fiscaux (dont {fr(t['foyers_imposes'])} imposés), " if t.get("foyers_imposes") is not None
                else f"{fr(t['foyers'])} foyers fiscaux, ")
        desc += f"revenu fiscal de référence cumulé : {fr(t['rfr_milliers'] * 1000)} €."
        if negatif:
            desc += " Montant négatif : sur cette tranche, les restitutions (crédits d'impôt…) dépassent l'impôt émis."
        return {"id": f"{prefixe}.{slugt(t['tranche'])}",
                "label": f"Foyers de {t['tranche'].replace(' dont:', '')} € de RFR" if not t["tranche"].startswith("Plus") else "Foyers de plus de 100 000 € de RFR",
                "montant": round(t["impot_net_milliers"] * 1000, 2), "annee": 2025, "statut": "confirme",
                "description": desc, "enfants": enfants or []}

    principales = [t for t in raw["tranches"] if t["tranche"] in PRINCIPALES]
    sous = [t for t in raw["tranches"] if t["tranche"] not in PRINCIPALES]
    assert abs(sum(t["impot_net_milliers"] for t in principales) - raw["total"]["impot_net_milliers"]) < 0.01
    assert abs(sum(t["impot_net_milliers"] for t in sous)
               - next(t["impot_net_milliers"] for t in principales if t["tranche"].startswith("Plus"))) < 0.01

    base = "etat.qui-paie.ir"
    enfants = []
    for t in principales:
        if t["tranche"].startswith("Plus"):
            kids = [noeud_tranche(s2, f"{base}.plus-de-100-000") for s2 in sous]
            enfants.append(noeud_tranche(t, base, kids))
        else:
            enfants.append(noeud_tranche(t, base))

    tot, dinr = raw["total"], raw["non_residents"]
    ir = {"id": base,
          "label": "L'impôt sur le revenu par tranche de revenu (revenus 2024, émis en 2025)",
          "montant": round(tot["impot_net_milliers"] * 1000, 2), "annee": 2025, "statut": "confirme",
          "description": (f"Impôt net émis par voie de rôle : {fr(tot['impot_net_milliers'] * 1000)} € payés par "
                          f"{fr(tot['foyers'])} foyers fiscaux, dont {fr(tot['foyers_imposes'])} imposés "
                          f"({fr(tot['foyers'] - tot['foyers_imposes'])} foyers non imposés). "
                          f"Dont non-résidents : {fr(dinr['impot_net_milliers'] * 1000)} € ({fr(dinr['foyers'])} foyers). "
                          f"Définition du fichier : « {raw['note_impot_net'][:220]}… » — ce périmètre (émission) diffère "
                          "de la ligne prévisionnelle de recettes de l'état A : les deux ne se comparent qu'avec précaution."),
          "source": src, "enfants": enfants}

    vue = {"id": "etat.qui-paie",
           "label": "🔎 Qui paie ? — l'impôt par profil de contribuable (vues non sommées)",
           "montant": None, "annee": 2025, "statut": "confirme",
           "description": ("Vues transverses : qui verse les recettes publiques. Le montant racine est volontairement null : "
                           "ces montants (constatés, millésime propre) ne s'additionnent pas aux lignes prévisionnelles des "
                           "recettes — aucun double compte. D'autres impôts (TVA, IS…) attendent leur ventilation : contribution bienvenue."),
           "source": {"nom": "Statistiques fiscales de la DGFiP (voir la source précise de chaque sous-vue)",
                      "url": "https://www.impots.gouv.fr/statistiques", "producteur": "DGFiP",
                      "licence": "Licence Ouverte 2.0", "consulte_le": meta["consulte_le"], "maj": None},
           "enfants": [ir]}

    def compte(n):
        return 1 + sum(compte(c) for c in n["enfants"])
    with open(os.path.join(ROOT, "data", "etat", "qui-paie.json"), "w", encoding="utf-8") as fh:
        json.dump(vue, fh, ensure_ascii=False, indent=1)
    print(f"vue « qui paie » : {compte(vue)} nœuds — impôt net total {tot['impot_net_milliers']*1000/1e9:.2f} Md€, sommes exactes")


if __name__ == "__main__":
    main()
