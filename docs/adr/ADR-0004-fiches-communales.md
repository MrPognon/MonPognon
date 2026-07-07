# ADR-0004 — Les fiches communales vivent hors de l'arbre national

- **Statut : Accepté** (2026-07-07, décision du mainteneur dans l'issue #21)
- **Date : 2026-07-07**

## Contexte

Le test terrain du parcours de contribution (07/2026, Châteauneuf-sur-Loire, 45082) a révélé un problème structurel : les **dépenses** d'une commune avaient un parent naturel (`coll.depenses.communes`), mais les **recettes** n'avaient aucune place — l'arbre des recettes des collectivités est ventilé **par nature** (fiscalité, dotations…), pas par commune.

Pire : insérer les communes individuelles dans l'arbre national crée un **double compte** mécanique côté recettes (la fiscalité d'une commune compterait dans « Fiscalité locale » ET dans la commune). Tolérable à une commune, total à 35 000.

Options examinées dans #21 : **A** — miroir `coll.recettes.communes` (double compte, nécessite d'exclure des branches de la somme) ; **B** — restructurer les recettes par échelon (migration, la vue par nature devient transverse) ; **C** — fiches hors arbre.

## Décision (option C)

1. **L'arbre national ne contient que des agrégats.** `coll.depenses.communes` reste le bloc communal national ; **aucune commune individuelle n'est sommée dans l'arbre national** → zéro double compte par construction.
2. **Une commune = un fichier** : `data/collectivites/communes/<n° département>/<code INSEE>.json` (découpage conforme à l'ADR-0002). Nœud racine `commune.<insee>` :
   - `montant: null` (dépenses et recettes ne s'additionnent pas) ;
   - deux enfants : `commune.<insee>.depenses` et `commune.<insee>.recettes` — **les recettes retrouvent leur place** ;
   - schéma **inchangé** : les fiches sont des nœuds ordinaires (mêmes règles de sourcing, mêmes statuts, mêmes contrôles de sommes à l'intérieur de chaque volet).
3. **Validation identique, publication différente** : `build.py` valide les fiches comme tout le reste (ids uniques globalement, sources, ±2 %), mais les publie en **fragments individuels** `site/data/communes/<insee>.json` — jamais dans `data.js`. Le site les chargera à la demande (sélecteur #3, fiche UX #18).
4. **Référence de millésime** : chaque fiche porte l'exercice dans ses nœuds (`annee`) ; plusieurs exercices pour une même commune = décision ADR-0003 (arbre par exercice) appliquée au moment où le besoin arrive.

## Conséquences

- `build.py` : routage `data/collectivites/communes/**` → fragments (implémenté dans la PR de cet ADR) ;
- kit IA + prompts : consigne « budget de ma commune » mise à jour (création d'un **nouveau fichier** via GitHub « Add file », plutôt qu'édition d'un fichier existant) ;
- la mission type « balances d'un département » (#17) produit directement des fiches à ce format ;
- le sélecteur de commune (#3) consommera `site/data/communes/<insee>.json` (statique, pas de CORS tiers) ;
- l'« exemple fondateur » est la fiche de Châteauneuf-sur-Loire (45082), issue du test terrain ;
- la comparaison entre communes (strates) reste hors périmètre de cet ADR (viendra avec #18).

## Rejeté

- **A** (miroir sous recettes) : double compte structurel, notion de « branche non sommée » ad hoc dans un arbre censé sommer.
- **B** (restructuration par échelon) : lourde migration immédiate pour un bénéfice que C obtient sans casser l'existant ; reste possible plus tard pour les agrégats nationaux.
