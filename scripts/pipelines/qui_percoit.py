#!/usr/bin/env python3
"""Génère la vue transverse « Qui perçoit ? » (issue #4) : data/etat/qui-percoit.json.

Deux sous-vues, chacune avec SON millésime (jamais sommées entre elles ni avec
l'arbre des dépenses — la racine porte un montant null : ces montants sont déjà
compris dans les crédits des programmes) :

- OPÉRATEURS DE L'ÉTAT (PLF 2025) : les 433 opérateurs et catégories du jaune,
  rattachés à leur mission et programme chefs de file. La liste open data ne
  publie pas les crédits par opérateur (a_completer → jaune PDF).
- SUBVENTIONS AUX ASSOCIATIONS (exécution 2023, annexe jaune du PLF 2025) :
  par programme (somme des versements du jeu) avec les 5 premières associations
  bénéficiaires telles quelles, et le reste compté en description.

Rejouable : relit les extraits bruts versionnés (data-sources/raw/), zéro appel
réseau. Usage : python3 scripts/pipelines/qui_percoit.py && python3 scripts/build.py
"""
import csv
import gzip
import io
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data-sources", "raw")


def slug(s, vus):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:40] or "x"
    base, i = s, 2
    while s in vus:
        s, i = f"{base}-{i}", i + 1
    vus.add(s)
    return s


def libelles_programmes():
    """code programme → libellé, depuis l'arbre des dépenses (source de vérité)."""
    lib = {}

    def walk(n):
        m = re.match(r"Programme (\d+) — (.+)", n.get("label", ""))
        if m:
            lib[m.group(1)] = m.group(2)
        for c in n.get("enfants", []):
            walk(c)

    walk(json.load(open(os.path.join(ROOT, "data", "etat", "depenses.json"), encoding="utf-8")))
    return lib


def vue_operateurs(meta):
    with gzip.open(os.path.join(RAW, "plf25-jaune-operateurs.csv.gz"), "rb") as fh:
        rows = list(csv.DictReader(io.StringIO(fh.read().decode(meta["encodage"])), delimiter=meta["separateur"]))
    cle_nom = next(k for k in rows[0] if k.startswith("Opérateur ou catégorie"))
    src = {"nom": "PLF 2025 — jaune « Opérateurs de l'État », liste des opérateurs et catégories",
           "url": meta["source_page"], "producteur": "Direction du budget",
           "licence": "Licence Ouverte 2.0", "consulte_le": meta["consulte_le"], "maj": meta["maj_dataset"]}
    missions, vus = {}, set()
    for r in rows:
        rattachement = (r.get("Mission et Programme chefs de file") or "").strip()
        lignes = [x.strip() for x in rattachement.split("\n") if x.strip()]
        mission = lignes[0] if lignes else "Rattachement non précisé"
        programme = lignes[1] if len(lignes) > 1 else None
        propre = lambda x: " ".join((x or "").split())   # espaces/retours internes normalisés
        nom = propre(r.get(cle_nom))
        membre = propre(r.get("Opérateur de la catégorie"))
        statut = propre(r.get("Statut"))
        mission, programme = propre(mission), propre(programme) if programme else None
        m = missions.setdefault(mission, {})
        p = m.setdefault(programme or "—", [])
        p.append({"nom": membre or nom, "categorie": nom if membre else None, "statut": statut})

    enfants_missions = []
    for mission in sorted(missions):
        id_mission = f"etat.qui-percoit.operateurs.{slug(mission, vus)}"
        enfants_prog = []
        for prog in sorted(missions[mission]):
            id_prog = f"{id_mission}.{slug(prog, vus)}"
            ops = missions[mission][prog]
            enfants_ops = [{
                "id": f"{id_prog}.{slug(o['nom'], vus)}",
                "label": o["nom"] + (f" (via la catégorie « {o['categorie']} »)" if o["categorie"] else ""),
                "montant": None, "annee": 2025, "statut": "confirme",
                "description": f"Statut juridique : {o['statut']}." if o["statut"] else None,
                "enfants": [],
            } for o in ops]
            for e in enfants_ops:
                if e["description"] is None:
                    e.pop("description")
            enfants_prog.append({
                "id": id_prog,
                "label": prog if prog != "—" else "Programme chef de file non précisé",
                "montant": None, "annee": 2025, "statut": "confirme", "enfants": enfants_ops,
            })
        enfants_missions.append({
            "id": id_mission,
            "label": mission, "montant": None, "annee": 2025, "statut": "confirme",
            "enfants": enfants_prog,
        })
    # Le financement par opérateur N'EST PAS dans ce jeu de données : la liste
    # publiée porte le nom, le statut juridique, la catégorie et le programme
    # chef de file — jamais un euro. On le déclare au lieu de laisser 433 nœuds
    # muets, conformément à la règle du dépôt sur les données manquantes.
    enfants_missions.append({
        "id": "etat.qui-percoit.operateurs.inconnu-financement",
        "label": "❓ Combien chaque opérateur reçoit-il ? — montants non publiés en données",
        "montant": None, "annee": None, "statut": "inconnu",
        "source": {"nom": "Constat d'absence — data.gouv.fr ne publie du jaune « Opérateurs de l'État » "
                          "que la liste des opérateurs et catégories (PLF 2024, 2025 et 2026 vérifiés "
                          "le 21/07/2026) : cinq colonnes, aucun montant.",
                   "url": "https://www.budget.gouv.fr/budget-etat/operateurs",
                   "producteur": "Direction du budget", "licence": "Licence Ouverte 2.0",
                   "consulte_le": "2026-07-21", "maj": None},
        "inconnu": {
            "quoi": "Le financement versé à chaque opérateur — 73 à 77 Md€ au total (subventions pour "
                    "charges de service public, dotations, transferts, taxes affectées). Il EXISTE, publié "
                    "dans le jaune « Opérateurs de l'État » annexé au PLF, mais en PDF seulement : la série "
                    "en format ouvert des budgets d'opérateurs est INTERROMPUE depuis le PLF 2019. "
                    "ATTENTION, PIÈGE DE LECTURE : même une fois les montants obtenus, la colonne « Mission "
                    "et Programme chefs de file » de la liste publiée ne dit PAS quel programme paie — un "
                    "chef de file est une attribution administrative, et un opérateur peut être financé par "
                    "plusieurs programmes. Rattacher un montant à son chef de file reviendrait à imputer un "
                    "agrégat à une ligne choisie : c'est exclu. Un rattachement suppose donc une source "
                    "donnant le programme PAYEUR par opérateur, pas seulement le chef de file.",
            "contact": "Direction du budget — reprise de la publication en format ouvert des budgets "
                       "d'opérateurs, interrompue après le PLF 2019",
            "url": "https://www.budget.gouv.fr/documentation/documents-budgetaires"},
        "enfants": []})

    return {
        "id": "etat.qui-percoit.operateurs",
        "label": f"Les opérateurs de l'État — {len(rows)} organismes (PLF 2025)",
        "montant": None, "annee": 2025, "statut": "confirme",
        "description": ("Agences, établissements et organismes financés et contrôlés par l'État (ADEME, universités, "
                        "Pôle emploi devenu France Travail…), rattachés à leur mission et programme chefs de file. "
                        "Leur financement est déjà compté dans les crédits des programmes (💸 Dépenses). "
                        "⚠️ Les montants par opérateur ne sont PAS affichés parce qu'ils ne sont pas publiés "
                        "en données ouvertes — voir le nœud « Combien chaque opérateur reçoit-il ? » en fin "
                        "de liste. Ce que cette vue apporte : le nom, le statut juridique, la catégorie de "
                        "rattachement et le programme chef de file de chacun des 433 organismes."),
        "source": src, "enfants": enfants_missions,
        "a_completer": {"note": "La liste open data ne publie pas les crédits par opérateur — ils figurent dans le jaune PDF « Opérateurs de l'État » (budget.gouv.fr) : contribution bienvenue, page à citer.",
                        "url": "https://www.budget.gouv.fr/documentation/documents-budgetaires"},
    }


def lignes_payeuses():
    """Programme → id du nœud qui le porte dans l'arbre des dépenses.
    C'est ce qui permet de rattacher un bénéficiaire nommé à la ligne qui l'a payé
    (niveau P5 de l'ADR-0006) : sans ce rattachement, on sait seulement qu'un
    organisme a reçu de l'argent, jamais QUELLE ligne budgétaire l'a versé."""
    with open(os.path.join(ROOT, "data", "etat", "depenses.json"), encoding="utf-8") as fh:
        arbre = json.load(fh)
    out = {}

    def walk(n, prof=0):
        if prof == 3:                      # profondeur du programme dans l'arbre
            out[n["id"].split(".")[-1]] = n["id"]
        for c in n.get("enfants", []):
            walk(c, prof + 1)

    walk(arbre)
    return out


def siren_propre(v):
    """Le jeu source porte « NR CHORUS » (461 lignes, 1,08 Md€) quand l'identifiant
    n'a pas été renseigné dans Chorus : on ne fabrique pas d'identifiant, on renvoie None."""
    s = " ".join(str(v or "").split()).replace(" ", "")
    return s if s.isdigit() and len(s) == 9 else None


def vue_associations(meta, lib, payeuses):
    with gzip.open(os.path.join(RAW, "plf25-jaune-associations.json.gz"), "rt", encoding="utf-8") as fh:
        rows = json.load(fh)
    src = {"nom": "PLF 2025 — annexe jaune « Effort financier de l'État en faveur des associations » (versements de l'exercice 2023)",
           "url": meta["url"], "producteur": "Direction du budget / DGFiP",
           "licence": "Licence Ouverte 2.0", "consulte_le": meta["consulte_le"], "maj": meta["maj_dataset"]}
    par_prog = {}
    for r in rows:
        if r.get("montant"):
            par_prog.setdefault(str(r["programme"]), []).append(r)
    total = sum(r["montant"] for lst in par_prog.values() for r in lst)
    vus = set()
    enfants_prog = []
    for prog, lst in sorted(par_prog.items(), key=lambda kv: -sum(r["montant"] for r in kv[1])):
        somme = sum(r["montant"] for r in lst)
        top = sorted(lst, key=lambda r: -r["montant"])[:5]
        reste_n, reste_m = len(lst) - len(top), somme - sum(r["montant"] for r in top)
        libelle = lib.get(prog)
        paye_par = payeuses.get(prog)
        enfants_assoc = []
        for t in top:
            sir = siren_propre(t.get("siren"))
            noeud = {
                "id": f"etat.qui-percoit.associations.p{prog}.{slug(t['denomination'] or 'association', vus)}",
                "label": " ".join((t["denomination"] or "(dénomination non renseignée)").split()).title(),
                "montant": round(t["montant"], 2), "annee": 2023, "statut": "confirme",
                "source": {"nom": src["nom"] + f", ligne du programme {prog}"},
            }
            # Ni identifiant ni rattachement ICI : ces cinq nœuds sont un APERÇU
            # d'affichage. La totalité des bénéficiaires vit dans les fragments
            # data/etat/subventions/<prog>.json, seule source du P5 — les porter
            # aux deux endroits ferait compter les mêmes euros deux fois.
            noeud["enfants"] = []
            enfants_assoc.append(noeud)
        enfants_prog.append({
            "id": f"etat.qui-percoit.associations.p{prog}",
            "label": f"Programme {prog}" + (f" — {libelle}" if libelle else "") + " : subventions aux associations",
            "montant": round(somme, 2), "annee": 2023, "statut": "confirme",
            "description": (f"{len(lst):,} versement(s) recensés en 2023 sur ce programme. Les 5 plus importants sont "
                            f"détaillés ci-dessous ; les {reste_n:,} autres représentent {reste_m:,.0f} €.").replace(",", " "),
            "enfants": enfants_assoc,
        })
    ecrire_fragments_subventions(rows, lib, payeuses, src)
    return {
        "id": "etat.qui-percoit.associations",
        "label": "Subventions de l'État aux associations (exécution 2023)",
        "montant": round(total, 2), "annee": 2023, "statut": "confirme",
        "description": (f"{len(rows):,} versements recensés dans l'annexe jaune, agrégés par programme budgétaire. "
                        "⚠️ Millésime 2023 (dernier exécuté publié) — ces montants sont déjà compris dans les dépenses "
                        "exécutées des programmes, ils ne s'additionnent pas au PLF 2025.").replace(",", " "),
        "source": src, "enfants": enfants_prog,
    }



def ecrire_fragments_subventions(rows, lib, payeuses, src):
    """Un fichier par programme sous data/etat/subventions/, contenant TOUS les
    bénéficiaires — pas seulement les cinq plus gros.

    Pourquoi des fragments et non la vue principale : les 112 722 versements
    pèsent ~31 Mo de JSON, et `site/data.js` (2,6 Mo) est chargé à chaque
    ouverture du site. Le mécanisme de fragments de l'ADR-0004, déjà utilisé
    pour les 56 491 fiches de collectivités, publie ces arbres à la demande
    SANS les inliner — tout en les gardant dans le calcul de l'indice, qui lit
    les arbres en mémoire et non le fichier publié.

    Racine à `bloc_univers: null` : cette vue est transverse, elle ne compte pas
    dans la couverture C. Elle ne sert qu'au reclassement P5, qui déplace des
    euros déjà comptés dans l'arbre payeur au lieu d'en ajouter."""
    dossier = os.path.join(ROOT, "data", "etat", "subventions")
    os.makedirs(dossier, exist_ok=True)
    par_prog = {}
    for r in rows:
        if r.get("montant"):
            par_prog.setdefault(str(r["programme"]), []).append(r)
    ecrits = rattaches = 0
    montant_rattache = 0.0
    for prog, lst in sorted(par_prog.items()):
        vus, enfants = set(), []
        paye_par = payeuses.get(prog)
        for r in sorted(lst, key=lambda x: -x["montant"]):
            sir = siren_propre(r.get("siren"))
            n = {
                "id": f"etat.subventions.p{prog}.{slug(r['denomination'] or 'association', vus)}",
                "label": " ".join((r["denomination"] or "(dénomination non renseignée)").split()).title(),
                "montant": round(r["montant"], 2), "annee": 2023, "statut": "confirme",
            }
            # P5 exige les DEUX : un identifiant machine ET la ligne payeuse.
            if sir:
                n["identifiant"] = {"type": "SIREN", "valeur": sir}
            if paye_par:
                n["rattachement_id"] = paye_par
                if sir:
                    rattaches += 1
                    montant_rattache += r["montant"]
            n["enfants"] = []
            enfants.append(n)
        racine = {
            "id": f"etat.subventions.p{prog}",
            "label": f"Programme {prog}" + (f" — {lib[prog]}" if lib.get(prog) else "")
                     + " : bénéficiaires des subventions aux associations",
            "montant": round(sum(r["montant"] for r in lst), 2), "annee": 2023, "statut": "confirme",
            "bloc_univers": None, "volet": None, "base_comptable": None,
            "niveaux": ["P0", "P5"],
            "description": (f"{len(lst):,} versement(s) de l'exercice 2023. Vue transverse : ces euros sont "
                            "DÉJÀ comptés dans les dépenses du programme payeur, ils ne s'y ajoutent pas."
                            ).replace(",", " "),
            "source": src, "enfants": enfants,
        }
        with open(os.path.join(dossier, f"{prog}.json"), "w", encoding="utf-8") as fh:
            json.dump(racine, fh, ensure_ascii=False, indent=1); fh.write("\n")
        ecrits += 1
    print(f"fragments subventions : {ecrits} programme(s), {rattaches} bénéficiaires rattachés "
          f"({montant_rattache/1e9:.3f} Md€ éligibles P5)")


def inconnues_vue():
    """Les inconnues structurelles du « qui perçoit » (issue #19, étude §6 — n° 11 et 12)."""
    return [
        {"id": "etat.qui-percoit.inconnu-consolide",
         "label": "❓ Subventions publiques consolidées (État + collectivités + Sécu)",
         "montant": None, "annee": None, "statut": "inconnu",
         "source": {"nom": "Constat d'absence — le jaune « associations » ne couvre que l'État (docs/etude-donnees.md §6)",
                    "url": "https://www.budget.gouv.fr/documentation/documents-budgetaires",
                    "producteur": "—", "licence": "Licence Ouverte 2.0", "consulte_le": "2026-07-09", "maj": None},
         "inconnu": {"quoi": "Une vue consolidée des ~23 Md€/an de subventions publiques, tous financeurs confondus (État + collectivités + organismes de sécurité sociale) — la sous-vue ci-dessus ne couvre que l'État.",
                     "contact": "Direction du Budget ; ou question parlementaire", "url": None}, "enfants": []},
        {"id": "etat.qui-percoit.inconnu-decp",
         "label": "❓ Commande publique : qui sont les fournisseurs de l'État (DECP)",
         "montant": None, "annee": None, "statut": "inconnu",
         "source": {"nom": "Constat de qualité — données essentielles de la commande publique consolidées défaillantes (docs/etude-donnees.md §6)",
                    "url": "https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides/",
                    "producteur": "—", "licence": "Licence Ouverte 2.0", "consulte_le": "2026-07-09", "maj": None},
         "inconnu": {"quoi": "Les marchés publics par attributaire, exploitables : les DECP consolidées souffrent de doublons et d'identifiants manquants (nouveau format unifié depuis 01/2024 — qualité à réévaluer avant intégration).",
                     "contact": "AIFE / data.gouv.fr", "url": None}, "enfants": []},
    ]


def main():
    meta_ops = json.load(open(os.path.join(RAW, "plf25-jaune-operateurs.meta.json"), encoding="utf-8"))
    meta_ass = json.load(open(os.path.join(RAW, "plf25-jaune-associations.meta.json"), encoding="utf-8"))
    lib = libelles_programmes()
    vue = {
        "id": "etat.qui-percoit",
        "label": "🔎 Qui perçoit ? — opérateurs et associations (vues non sommées)",
        "montant": None, "annee": 2025, "statut": "confirme",
        "description": ("Vues transverses : à qui va l'argent des programmes. Le montant racine est volontairement null : "
                        "ces sommes sont déjà comptées dans les crédits des programmes (aucun double compte), et chaque "
                        "sous-vue porte son propre millésime."),
        "source": {"nom": "Annexes « jaunes » du PLF 2025 (voir la source précise de chaque sous-vue)",
                   "url": "https://www.budget.gouv.fr/documentation/documents-budgetaires",
                   "producteur": "Direction du budget", "licence": "Licence Ouverte 2.0",
                   "consulte_le": meta_ops["consulte_le"], "maj": None},
        "enfants": [vue_operateurs(meta_ops), vue_associations(meta_ass, lib, lignes_payeuses()), *inconnues_vue()],
    }
    def compte(n): return 1 + sum(compte(c) for c in n["enfants"])
    with open(os.path.join(ROOT, "data", "etat", "qui-percoit.json"), "w", encoding="utf-8") as fh:
        json.dump(vue, fh, ensure_ascii=False, indent=1)
    print(f"vue « qui perçoit » : {compte(vue)} nœuds "
          f"(opérateurs : {compte(vue['enfants'][0])}, associations : {compte(vue['enfants'][1])})")


if __name__ == "__main__":
    main()
