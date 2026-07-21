#!/usr/bin/env python3
"""Qualifie chaque arbre pour l'indice C·P (ADR-0006, étape 3 de l'issue #50).

Ajoute quatre champs à la RACINE de chaque fichier de données :

  bloc_univers  code du sous-segment du dénominateur que cet arbre alimente
                (data/denominateurs/apu-*.json), ou null si l'arbre ne compte
                PAS dans la couverture — vues transverses non sommées, agrégats
                estimés doublonnant une couverture portée ailleurs, volets dont
                le dénominateur n'est pas encore ouvert.

  volet         "depenses" | "recettes" | "mixte" (les deux volets sous une même
                racine, cas des fiches communales) | null (vue transverse). Sans
                lui, le calcul mélangerait l'arbre des dépenses et celui des
                recettes, qui se mesurent contre deux dénominateurs distincts.

  base_comptable  comptabilité dans laquelle les montants de cet arbre sont
                libellés ("PLF", "OFGL", "CCSS"), ou null si l'arbre ne compte
                pas. C'est ce champ que build.py compare à celui du référentiel
                du bloc pour REFUSER un coefficient mesuré entre deux
                comptabilités différentes (ADR-0007). Sans lui, la règle
                anti-triche n'était qu'une convention de relecture.

  niveaux       table de traduction « profondeur JSON → niveau de destination »
                sur l'échelle P0→P6 de l'ADR-0006. Un `null` signifie que ce
                cran N'AVANCE PAS l'axe destination : l'euro conserve alors le
                dernier niveau non nul au-dessus de lui.

Le `null` est le point délicat. L'axe P mesure JUSQU'OÙ ON SUIT L'EURO, pas la
finesse de la description. Ventiler une sous-action par titre LOLF (personnel,
fonctionnement, investissement) dit COMMENT l'argent est dépensé, jamais À QUI
il va : ce cran ne doit donc rien rapporter. Même raisonnement pour la
ventilation d'une commune par nature de dépense.

ATTENTION — qualifier finement un bloc dont le coefficient de couverture est NUL
ne rapporte RIEN, ni sur C ni sur P. build.py calcule `comptes = c * poids_eur` :
avec c = 0, aucun euro du bloc n'entre dans l'histogramme de profondeur. Pousser
tout l'arbre de la Sécu à P6 laisse P strictement inchangé. Le comportement est
voulu (sans lui, la faille que la règle du référentiel homogène ferme sur C se
rouvrirait par P), mais il rend inutile tout travail de profondeur sur les blocs
non raccordés : ASSO.regimes, ASSO.odass, APUC.odac, APUL.odal. Voir l'ADR-0006,
note d'application 3.

Idempotent : relancer le script ne change rien si les valeurs sont déjà à jour.

    python3 scripts/pipelines/qualifier_profondeur.py [--verifier]
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Table de qualification, fichier par fichier ──────────────────────────────
# Les niveaux sont indexés par profondeur JSON (0 = racine du fichier).
QUALIF = {
    "data/etat/depenses.json": (
        "APUC.etat", "depenses", "PLF",
        # racine, titre budgétaire (BG/CAS/CCF/BA), mission, programme,
        # action, sous-action, titre LOLF (nature → n'avance pas la destination)
        ["P0", "P0", "P1", "P2", "P3", "P3", None],
    ),
    "data/etat/recettes.json": (
        "APUC.etat", "recettes", "PLF",   # les 156 lignes de l'état A
        ["P0", "P1", "P2"],
    ),
    "data/etat/qui-percoit.json": (
        None, None, None,  # vue transverse, montant racine null, jamais sommée (issue #4)
        ["P0", "P0", "P1", "P2", "P4"],
    ),
    "data/etat/qui-paie.json": (
        None, None, None,  # vue transverse, montant racine null, jamais sommée (issue #5)
        ["P0", "P0", "P1", "P2"],
    ),
    "data/secu/depenses.json": (
        "ASSO.regimes", "depenses", "CCSS",
        ["P0", "P1", "P2", "P3"],
    ),
    "data/secu/recettes.json": (
        "ASSO.regimes", "recettes", "CCSS",
        ["P0", "P1", "P2", "P3"],
    ),
    "data/collectivites/depenses.json": (
        # Agrégat national « estimé ». La couverture locale est portée par les
        # fiches communales : le rattacher à APUL doublonnerait.
        None, "depenses", None,
        ["P0", "P1"],
    ),
    "data/collectivites/recettes.json": (
        None, "recettes", None,
        ["P0", "P1"],
    ),
}

# Fiches de collectivités (ADR-0004) : l'entité est nommée (P2) ; sa ventilation
# interne par nature de dépense n'avance pas l'axe destination. Un échelon = un bloc.
NIVEAUX_FICHE = ["P2", "P2", "P2", None, None, None]
FICHES_ECHELONS = {
    "communes": "APUL.communes",
    "groupements": "APUL.communes",   # EPCI : même bloc SEC que les communes
    "departements": "APUL.departements",
    "regions": "APUL.regions",
    "syndicats": "APUL.syndicats",
    "ccas": "APUL.odal",
    "sdis": "APUL.odal",
}

NIVEAUX_VALIDES = {"P0", "P1", "P2", "P3", "P4", "P5", "P6", None}


CHAMPS = ("bloc_univers", "volet", "base_comptable", "niveaux")


def poser_champs(node, bloc, volet, base, niveaux):
    """Insère les champs de qualification juste après `statut`, en préservant
    l'ordre des autres clés (la position compte pour la lisibilité des diffs)."""
    valeurs = (bloc, volet, base, niveaux)
    if all(node.get(k, "∅") == v for k, v in zip(CHAMPS, valeurs)):
        return False
    for k in CHAMPS:
        node.pop(k, None)
    cles = list(node.keys())
    ancre = cles.index("statut") + 1 if "statut" in cles else len(cles)
    reste = cles[ancre:]
    for k, v in zip(CHAMPS, valeurs):
        node[k] = v
    for k in reste:                      # on repousse la fin pour garder l'ordre
        node[k] = node.pop(k)
    return True


def profondeur_max(n, p=0):
    return max([profondeur_max(c, p + 1) for c in n.get("enfants", [])] or [p])


def main():
    verifier = "--verifier" in sys.argv
    modifies = erreurs = 0

    cibles = list(QUALIF.items())
    for ech, bloc in FICHES_ECHELONS.items():
        motif = ("*", "*.json") if ech == "communes" else ("*.json",)
        for f in sorted(glob.glob(os.path.join(ROOT, "data", "collectivites", ech, *motif))):
            # Toutes les fiches de collectivités viennent de l'OFGL (ADR-0004).
            cibles.append((os.path.relpath(f, ROOT), (bloc, "mixte", "OFGL", NIVEAUX_FICHE)))

    for rel, (bloc, volet, base, niveaux) in cibles:
        chemin = os.path.join(ROOT, rel)
        with open(chemin, encoding="utf-8") as fh:
            node = json.load(fh)

        assert all(n in NIVEAUX_VALIDES for n in niveaux), rel
        pmax = profondeur_max(node)
        if pmax >= len(niveaux):
            print(f"ERREUR {rel}: profondeur max {pmax} > table de {len(niveaux)} niveaux", file=sys.stderr)
            erreurs += 1
            continue

        if poser_champs(node, bloc, volet, base, niveaux):
            modifies += 1
            if not verifier:
                with open(chemin, "w", encoding="utf-8") as fh:
                    json.dump(node, fh, ensure_ascii=False, indent=1)   # indent=1 : format du dépôt
                    fh.write("\n")

    if erreurs:
        sys.exit(1)
    verbe = "à qualifier" if verifier else "qualifié(s)"
    print(f"OK — {len(cibles)} fichier(s) parcouru(s), {modifies} {verbe}")


if __name__ == "__main__":
    main()
