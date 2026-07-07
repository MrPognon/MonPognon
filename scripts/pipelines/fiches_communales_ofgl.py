#!/usr/bin/env python3
"""Génère les fiches communales (ADR-0004) d'un département à partir des
agrégats OFGL — pipeline de la mission « balances d'un département » (#17).

- Lit l'extrait brut VERSIONNÉ data-sources/raw/ofgl-communes-<dept>-<exer>.json.gz
  (zéro appel réseau par défaut ; le raw et sa provenance .meta.json font foi).
- Une commune = un fichier data/collectivites/communes/<dept>/<insee>.json,
  structure identique à la fiche fondatrice 45082 : racine commune.<insee>
  (montant null) + depenses (fonctionnement + investissement, sous-postes)
  + recettes (idem, investissement partiel).
- RIGUEUR : les sous-niveaux ne sont émis QUE si leur somme réconcilie le
  parent au centime (fonctionnement, investissement, total) — sinon la fiche
  reste au niveau sûr et la commune est listée dans le rapport.
- Les fiches déjà présentes ne sont JAMAIS écrasées (enrichissements manuels
  préservés, ex. 45082) — --forcer pour outrepasser.

Usage : python3 scripts/pipelines/fiches_communales_ofgl.py --departement 45 --exercice 2024
Puis  : python3 scripts/build.py   (validation + fragments site/data/communes/)
"""
import glob
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sous-postes OFGL dont la somme doit reconstituer exactement le parent.
DEP_FCT = ["Frais de personnel", "Achats et charges externes", "Dépenses d'intervention",
           "Autres dépenses de fonctionnement", "Charges financières"]
DEP_INV = ["Dépenses d'équipement", "Remboursements d'emprunts hors GAD",
           "Autres dépenses d'investissement", "Subventions d'équipement versées"]
REC_FCT = ["Impôts et taxes", "Concours de l'Etat", "Ventes de biens et services",
           "Subventions reçues et participations", "Autres recettes de fonctionnement"]
REC_INV = ["Emprunts hors GAD", "FCTVA", "Autres recettes d'investissement"]
# NB : « Produit des cessions d'immobilisations » est volontairement exclu — l'agrégat
# recouvre « Autres recettes d'investissement » pour certaines communes (constaté sur
# 13 communes du Loiret, ex. 45008), ce qui ferait dépasser le total.
SLUG = {"Frais de personnel": "personnel", "Achats et charges externes": "achats",
        "Dépenses d'intervention": "intervention", "Autres dépenses de fonctionnement": "autres",
        "Charges financières": "charges-financieres", "Dépenses d'équipement": "equipement",
        "Remboursements d'emprunts hors GAD": "remboursement-emprunts",
        "Autres dépenses d'investissement": "autres", "Subventions d'équipement versées": "subventions-versees",
        "Impôts et taxes": "impots", "Concours de l'Etat": "concours-etat",
        "Ventes de biens et services": "ventes", "Subventions reçues et participations": "subventions-participations",
        "Autres recettes de fonctionnement": "autres", "Emprunts hors GAD": "emprunts",
        "FCTVA": "fctva", "Autres recettes d'investissement": "autres",
        "Produit des cessions d'immobilisations": "cessions"}
LIBELLE = {"Concours de l'Etat": "Concours de l'État (dont DGF)",
           "Remboursements d'emprunts hors GAD": "Remboursements d'emprunts (hors gestion active de la dette)",
           "Emprunts hors GAD": "Emprunts (hors gestion active de la dette)",
           "FCTVA": "FCTVA (remboursement de TVA sur investissements)"}


def source(meta, agregat=None):
    detail = f", agrégat « {agregat} »" if agregat else ""
    return {"nom": f"OFGL — Comptes des communes 2017-2024 (jeu ofgl-base-communes), budget principal, exercice 2024{detail}",
            "url": meta["url"], "producteur": "OFGL / DGFiP", "licence": "Licence Ouverte 2.0",
            "consulte_le": meta["consulte_le"], "maj": meta["maj_dataset"]}


def centime(a, b):
    return abs(a - b) < 0.01


def fiche_commune(insee, dept, rows, meta, rapport):
    ag = {r["agregat"]: r["montant"] for r in rows if r["montant"] is not None}
    nom, ptot, nomen, epci = rows[0]["com_name"], rows[0].get("ptot"), rows[0].get("nomen"), rows[0].get("epci_name")
    exer = 2024

    def noeud(ide, label, montant, agregat, enfants=None, desc=None):
        n = {"id": ide, "label": label, "montant": round(montant, 2), "annee": exer,
             "statut": "confirme", "source": source(meta, agregat), "enfants": enfants or []}
        if desc:
            n["description"] = desc
        return n

    def sous_postes(parent_id, parent_val, postes, exiger_egalite):
        present = [(p, ag[p]) for p in postes if p in ag]
        total = sum(v for _, v in present)
        if exiger_egalite and not centime(total, parent_val):
            rapport.setdefault("sans_sous_postes", []).append(f"{insee} {'.'.join(parent_id.split('.')[-2:])} ({total:,.2f} vs {parent_val:,.2f})")
            return []
        if not exiger_egalite and total > parent_val + 0.01:
            rapport.setdefault("sans_sous_postes", []).append(f"{insee} {'.'.join(parent_id.split('.')[-2:])} (dépassement : {total:,.2f} vs {parent_val:,.2f})")
            return []
        enfants = [noeud(f"{parent_id}.{SLUG[p]}", LIBELLE.get(p, p), v, p) for p, v in present]
        rapport.setdefault("_partiels", set())
        if enfants and total < parent_val - 0.01:
            rapport["_partiels"].add(parent_id)
        return enfants

    def volet(cle, label_volet, tot_a, fct_a, inv_a, fct_postes, inv_postes, inv_partiel):
        if tot_a not in ag or fct_a not in ag or inv_a not in ag:
            rapport.setdefault("agregats_absents", []).append(insee)
            return None
        tot, fct, inv = ag[tot_a], ag[fct_a], ag[inv_a]
        if not centime(fct + inv, tot):
            rapport.setdefault("non_reconcilie", []).append(f"{insee} {cle} ({fct + inv:,.2f} vs {tot:,.2f})")
            return noeud(f"commune.{insee}.{cle}", f"{label_volet} {exer} (budget principal)", tot, tot_a)
        base = f"commune.{insee}.{cle}"
        DESC_PARTIEL = ("Ventilation partielle : postes principaux uniquement — la somme des enfants est "
                        "inférieure au total, le reliquat correspond à d'autres agrégats OFGL non repris ici.")
        kids_fct = sous_postes(f"{base}.fonctionnement", fct, fct_postes, True)
        kids_inv = sous_postes(f"{base}.investissement", inv, inv_postes, False)
        return noeud(base, f"{label_volet} {exer} (budget principal)", tot, tot_a, [
            noeud(f"{base}.fonctionnement", f"{label_volet.split(' ')[0]} de fonctionnement", fct, fct_a,
                  kids_fct, DESC_PARTIEL if f"{base}.fonctionnement" in rapport.get("_partiels", set()) else None),
            noeud(f"{base}.investissement", f"{label_volet.split(' ')[0]} d'investissement", inv, inv_a,
                  kids_inv, DESC_PARTIEL if f"{base}.investissement" in rapport.get("_partiels", set()) else None),
        ])

    dep = volet("depenses", "Dépenses", "Dépenses totales", "Dépenses de fonctionnement",
                "Dépenses d'investissement", DEP_FCT, DEP_INV, False)
    rec = volet("recettes", "Recettes", "Recettes totales", "Recettes de fonctionnement",
                "Recettes d'investissement", REC_FCT, REC_INV, True)
    if not dep or not rec:
        return None
    d_m, r_m = dep["montant"], rec["montant"]
    fmt = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return {"id": f"commune.{insee}", "label": f"{nom} (Loiret, {insee})", "montant": None,
            "annee": exer, "statut": "confirme",
            "description": (f"Fiche communale (ADR-0004) — {nom}, code INSEE {insee}, Loiret"
                            + (f", {int(ptot):,} habitants (population DGF {exer})".replace(",", " ") if ptot else "")
                            + (f", membre de « {epci} »" if epci else "")
                            + f". Comptes {exer} exécutés, budget principal, nomenclature {nomen or 'M57'}, hors budgets annexes. "
                            f"Le montant racine est volontairement null : les dépenses ({fmt(d_m)} €) et les recettes "
                            f"({fmt(r_m)} €) ne s'additionnent pas."),
            "source": source(meta), "enfants": [dep, rec]}


def main():
    dept = sys.argv[sys.argv.index("--departement") + 1] if "--departement" in sys.argv else "45"
    forcer = "--forcer" in sys.argv
    raw_p = os.path.join(ROOT, "data-sources", "raw", f"ofgl-communes-{dept}-2024.json.gz")
    meta = json.load(open(raw_p.replace(".json.gz", ".meta.json"), encoding="utf-8"))
    with gzip.open(raw_p, "rt", encoding="utf-8") as fh:
        rows = json.load(fh)
    par_commune = {}
    for r in rows:
        par_commune.setdefault(r["insee"], []).append(r)

    out_dir = os.path.join(ROOT, "data", "collectivites", "communes", dept)
    os.makedirs(out_dir, exist_ok=True)
    rapport, ecrites, gardees = {}, 0, 0
    for insee in sorted(par_commune):
        chemin = os.path.join(out_dir, f"{insee}.json")
        if os.path.exists(chemin) and not forcer:
            gardees += 1
            continue
        fiche = fiche_commune(insee, dept, par_commune[insee], meta, rapport)
        if fiche is None:
            continue
        with open(chemin, "w", encoding="utf-8") as fh:
            json.dump(fiche, fh, ensure_ascii=False, indent=1)
        ecrites += 1

    print(f"communes du raw : {len(par_commune)} | fiches écrites : {ecrites} | "
          f"préservées (déjà au dépôt) : {gardees}")
    partiels = len(rapport.pop("_partiels", set()))
    if partiels:
        print(f"ℹ ventilations partielles (somme < total, décrites comme telles) : {partiels}")
    for cle, val in rapport.items():
        if isinstance(val, list):
            print(f"⚠ {cle} : {len(val)}")
            for v in val[:8]:
                print(f"   {v}")
    if not rapport:
        print("réconciliations : totales = fonctionnement + investissement au centime, partout ✅")


if __name__ == "__main__":
    main()
