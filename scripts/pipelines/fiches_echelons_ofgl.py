#!/usr/bin/env python3
"""Génère les fiches des AUTRES échelons de collectivités (ADR-0004) à partir des
agrégats consolidés de l'OFGL : départements, régions, syndicats.

Frère du pipeline communal, dont il IMPORTE les listes de sous-postes, les slugs
et les libellés — ces constantes sont la partie fragile et ne doivent exister
qu'une fois. Vérifié avant écriture : les sous-postes communaux réconcilient AU
CENTIME pour un département comme pour une région.

Différences assumées avec le pipeline communal :
- jeux CONSOLIDÉS (`-consolidee`), donc budget principal + budgets annexes, ce qui
  correspond exactement au référentiel de comptage du dénominateur — pas de biais
  de sous-estimation à déclarer, contrairement aux communes ;
- une seule extraction brute par échelon (97 départements, 17 régions,
  8 743 syndicats), sans découpage par département ;
- pas d'écrasement des fiches déjà présentes, comme pour les communes.

RIGUEUR : les sous-niveaux ne sont émis QUE si leur somme réconcilie le parent au
centime ; sinon la fiche reste au niveau sûr et l'entité est listée au rapport.
Sortie non nulle dès qu'un invariant casse.

Usage : python3 scripts/pipelines/fiches_echelons_ofgl.py --echelon departements [--telecharger]
Puis  : python3 scripts/build.py
"""
import datetime
import gzip
import json
import os
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fiches_communales_ofgl import (  # noqa: E402  — la partie fragile n'existe qu'une fois
    DEP_FCT, DEP_INV, REC_FCT, REC_INV, SLUG, LIBELLE, centime)

DESC_PARTIEL = ("Ventilation partielle : postes principaux uniquement — la somme des enfants est "
                "inférieure au total, le reliquat correspond à d'autres agrégats OFGL non repris ici.")

# ── Configuration par échelon ────────────────────────────────────────────────
ECHELONS = {
    "departements": {
        "jeu": "ofgl-base-departements-consolidee", "cle": "dep_code", "nom_champ": "dep_name",
        "prefixe": "departement", "dossier": "departements", "bloc": "APUL.departements",
        "libelle_jeu": "Comptes consolidés des départements", "quoi": "Fiche départementale",
    },
    "regions": {
        "jeu": "ofgl-base-regions-consolidee", "cle": "reg_code", "nom_champ": "reg_name",
        "prefixe": "region", "dossier": "regions", "bloc": "APUL.regions",
        "libelle_jeu": "Comptes consolidés des régions", "quoi": "Fiche régionale",
    },
    "syndicats": {
        "jeu": "ofgl-base-syndicats-consolidee", "cle": "siren", "nom_champ": "synd_name",
        "sans_population": True,   # ce jeu ne porte pas de champ ptot
        "prefixe": "syndicat", "dossier": "syndicats", "bloc": "APUL.syndicats",
        "libelle_jeu": "Comptes consolidés des syndicats", "quoi": "Fiche de syndicat",
    },
}
EXER = 2024


def source(cfg, meta, agregat=None):
    detail = f", agrégat « {agregat} »" if agregat else ""
    return {"nom": f"OFGL — {cfg['libelle_jeu']} (jeu {cfg['jeu']}), comptes consolidés, "
                   f"exercice {EXER}{detail}",
            "url": meta["url"], "producteur": "OFGL / DGFiP", "licence": "Licence Ouverte 2.0",
            "consulte_le": meta["consulte_le"], "maj": meta["maj_dataset"]}


def telecharger(cfg, raw_p):
    """(Re)crée l'extrait brut versionné + sa provenance depuis l'API OFGL."""
    api = f"https://data.ofgl.fr/api/explore/v2.1/catalog/datasets/{cfg['jeu']}"
    where = urllib.parse.quote(f"year(exer)={EXER}")
    champs = [cfg["cle"], cfg["nom_champ"], "exer", "agregat", "montant"]
    if not cfg.get("sans_population"):
        champs.append("ptot")
    select = ",".join(champs)
    r = subprocess.run(["curl", "-fsSL", "--compressed", "--max-time", "300",
                        f"{api}/exports/json?where={where}&select={select}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"téléchargement OFGL impossible ({cfg['jeu']})")
    rows = json.loads(r.stdout)
    meta_api = json.loads(subprocess.run(["curl", "-fsSL", api], capture_output=True, text=True).stdout)
    maj = (meta_api.get("metas", {}).get("default", {}).get("modified") or "")[:10] or None
    with gzip.open(raw_p, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)
    meta = {"dataset": cfg["jeu"], "filtre": f"year(exer)={EXER}",
            "consulte_le": datetime.date.today().isoformat(), "maj_dataset": maj,
            "lignes": len(rows), "url": f"https://data.ofgl.fr/explore/dataset/{cfg['jeu']}/"}
    with open(raw_p.replace(".json.gz", ".meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(f"raw téléchargé : {len(rows)} lignes, maj dataset {maj}")


def fiche(cle_val, rows, cfg, meta, rapport):
    ag = {r["agregat"]: r["montant"] for r in rows if r.get("montant") is not None}
    nom = rows[0].get(cfg["nom_champ"]) or f"{cfg['prefixe']} {cle_val}"
    ptot = rows[0].get("ptot")
    racine = f"{cfg['prefixe']}.{cle_val}"

    def noeud(ide, label, montant, agregat, enfants=None, desc=None):
        n = {"id": ide, "label": label, "montant": round(montant, 2), "annee": EXER,
             "statut": "confirme", "source": source(cfg, meta, agregat), "enfants": enfants or []}
        if desc:
            n["description"] = desc
        return n

    def sous_postes(parent_id, parent_val, postes):
        presents = [(p, ag[p]) for p in postes if p in ag]
        if not presents:
            return []
        somme = sum(v for _, v in presents)
        if somme > parent_val + 0.01:          # dépassement : on n'invente pas de ventilation
            return []
        if not centime(somme, parent_val):
            rapport.setdefault("_partiels", set()).add(parent_id)
        return [noeud(f"{parent_id}.{SLUG[p]}", LIBELLE.get(p, p), v, p) for p, v in presents]

    def volet(cle, label_volet, tot_a, fct_a, inv_a, fct_postes, inv_postes):
        if tot_a not in ag or fct_a not in ag or inv_a not in ag:
            rapport.setdefault("agregats_absents", []).append(str(cle_val))
            return None
        tot, fct, inv = ag[tot_a], ag[fct_a], ag[inv_a]
        base = f"{racine}.{cle}"
        if not centime(fct + inv, tot):
            rapport.setdefault("non_reconcilie", []).append(f"{cle_val} {cle}")
            return noeud(base, f"{label_volet} {EXER} (comptes consolidés)", tot, tot_a)
        kids_fct = sous_postes(f"{base}.fonctionnement", fct, fct_postes)
        kids_inv = sous_postes(f"{base}.investissement", inv, inv_postes)
        part = rapport.get("_partiels", set())
        return noeud(base, f"{label_volet} {EXER} (comptes consolidés)", tot, tot_a, [
            noeud(f"{base}.fonctionnement", f"{label_volet.split(' ')[0]} de fonctionnement", fct, fct_a,
                  kids_fct, DESC_PARTIEL if f"{base}.fonctionnement" in part else None),
            noeud(f"{base}.investissement", f"{label_volet.split(' ')[0]} d'investissement", inv, inv_a,
                  kids_inv, DESC_PARTIEL if f"{base}.investissement" in part else None),
        ])

    dep = volet("depenses", "Dépenses", "Dépenses totales", "Dépenses de fonctionnement",
                "Dépenses d'investissement", DEP_FCT, DEP_INV)
    rec = volet("recettes", "Recettes", "Recettes totales", "Recettes de fonctionnement",
                "Recettes d'investissement", REC_FCT, REC_INV)
    if not dep or not rec:
        return None
    fmt = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return {"id": racine, "label": f"{nom} ({cle_val})", "montant": None,
            "annee": EXER, "statut": "confirme",
            "bloc_univers": cfg["bloc"], "volet": "mixte",
            "niveaux": ["P2", "P2", "P2", None, None, None],
            "description": (f"{cfg['quoi']} (ADR-0004) — {nom}, code {cle_val}"
                            + (f" · {int(ptot):,} habitants".replace(",", "\u202f") if ptot else "")
                            + f". Comptes {EXER} exécutés, CONSOLIDÉS (budget principal et budgets annexes). "
                            f"Le montant racine est volontairement null : les dépenses ({fmt(dep['montant'])} €) "
                            f"et les recettes ({fmt(rec['montant'])} €) ne s'additionnent pas."),
            "source": source(cfg, meta), "enfants": [dep, rec]}


def main():
    if "--echelon" not in sys.argv:
        raise SystemExit("usage : --echelon " + "|".join(ECHELONS))
    ech = sys.argv[sys.argv.index("--echelon") + 1]
    if ech not in ECHELONS:
        raise SystemExit(f"échelon inconnu « {ech} » — attendu : {', '.join(ECHELONS)}")
    cfg, forcer = ECHELONS[ech], "--forcer" in sys.argv
    raw_p = os.path.join(ROOT, "data-sources", "raw", f"ofgl-{ech}-{EXER}.json.gz")

    # Le brut versionné fait foi (même règle que le pipeline communal).
    if "--telecharger" in sys.argv:
        if os.environ.get("CI"):
            sys.exit("ERREUR : --telecharger est refusé en CI — le brut versionné fait foi.")
        telecharger(cfg, raw_p)
    elif not os.path.exists(raw_p):
        sys.exit(f"ERREUR : extrait brut absent — {os.path.relpath(raw_p, ROOT)}\n"
                 f"        Pour le créer hors CI : --echelon {ech} --telecharger")

    meta = json.load(open(raw_p.replace(".json.gz", ".meta.json"), encoding="utf-8"))
    with gzip.open(raw_p, "rt", encoding="utf-8") as fh:
        rows = json.load(fh)
    par_entite = {}
    for r in rows:
        if r.get(cfg["cle"]):
            par_entite.setdefault(str(r[cfg["cle"]]), []).append(r)

    out_dir = os.path.join(ROOT, "data", "collectivites", cfg["dossier"])
    os.makedirs(out_dir, exist_ok=True)
    rapport, ecrites, gardees = {}, 0, 0
    for cle_val in sorted(par_entite):
        chemin = os.path.join(out_dir, f"{cle_val}.json")
        if os.path.exists(chemin) and not forcer:
            gardees += 1
            continue
        f = fiche(cle_val, par_entite[cle_val], cfg, meta, rapport)
        if f is None:
            continue
        with open(chemin, "w", encoding="utf-8") as fh:
            json.dump(f, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        ecrites += 1

    print(f"{ech} : {len(par_entite)} entités | écrites : {ecrites} | préservées : {gardees}")
    partiels = len(rapport.pop("_partiels", set()))
    if partiels:
        print(f"ℹ ventilations partielles : {partiels}")
    for cle, val in rapport.items():
        print(f"⚠ {cle} : {len(val)}")
        for v in val[:8]:
            print(f"   {v}")
    if not rapport:
        print("réconciliations : totales = fonctionnement + investissement au centime, partout ✅")

    manquantes = len(par_entite) - (ecrites + gardees)
    if rapport or manquantes:
        detail = []
        if rapport:
            detail.append("invariants cassés : " + ", ".join(f"{k} ({len(v)})" for k, v in rapport.items()))
        if manquantes:
            detail.append(f"{manquantes} entité(s) du brut sans fiche produite")
        sys.exit("ERREUR : " + " ; ".join(detail))


if __name__ == "__main__":
    main()
