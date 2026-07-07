# ADR-0002 — Stratégie data à l'échelle : fichiers découpés, pipelines pour la masse

- **Statut : Proposé** (décision à prendre dans la PR — commentaires bienvenus)
- **Date : 2026-07-07**

## Contexte

L'ambition : chaque euro, jusqu'aux ~35 000 communes (puis EPCI, opérateurs, associations). Le dispositif actuel ne tient pas cette échelle :

1. **Fichiers monolithiques** — `data/etat/depenses.json` porte déjà ~1 200 nœuds dans un seul fichier : conflits de merge garantis entre PRs simultanées, éditions pénibles, diffs illisibles.
2. **Contribution uniquement manuelle** — ajouter 35 000 communes par éditions à la main est impossible, et relire 35 000 nœuds un par un aussi. Le goulot de revue est LE risque n°1 du projet en cas de succès.

## Décision proposée (quatre volets)

### 1. Découper les fichiers sources par périmètre

- `data/etat/depenses/<mission>.json` (une mission par fichier), `data/etat/recettes.json` (gardé, taille ok) ;
- `data/collectivites/communes/<departement>/<code-insee>.json` (à terme) ;
- `build.py` **assemble** les fichiers en arbres (l'id hiérarchique donne déjà l'emplacement — l'assemblage est déterministe), et continue de tout valider globalement (unicité des ids inter-fichiers).
- Migration à faire une fois, par script, sans changement de contenu (diff sémantiquement vide).

### 2. La donnée de masse entre par pipelines, pas par PRs manuelles

- Un **pipeline** = un script versionné dans `scripts/pipelines/` qui va d'une source officielle (API) aux fichiers `data/`, rejouable par n'importe qui ;
- la PR d'un pipeline contient : le script + les extraits bruts (`data-sources/raw/`) + le log d'exécution + les fichiers générés. **On relit le script, pas les 35 000 nœuds** ;
- un pipeline rejoué doit produire un diff vide (déterminisme) — c'est le critère de confiance ;
- les PRs manuelles restent le canal des corrections fines, des nœuds `inconnu`, des cas particuliers.

### 3. Sorties fragmentées

`build.py` génère des fragments par branche (chargés à la demande par le site) au lieu d'un `data.js` unique — déjà esquissé (#7), rendu obligatoire par l'échelle. Format cible à préciser dans l'implémentation (fragments JSON + index).

### 4. Ce qui ne change pas

Le schéma des nœuds, la règle d'or du sourcing, la CI de validation, le format de contribution simple (un JSON lisible) pour les cas fins.

## Alternatives écartées

- **Base de données** (SQLite/Postgres + API) : casse le modèle « le repo EST la donnée » (auditabilité git, PRs = contributions, hosting statique gratuit). À reconsidérer seulement si git ne tient plus le volume (des dizaines de milliers de petits fichiers JSON restent dans la zone de confort de git).
- **Monorepo data séparé** : prématuré ; à revisiter si le poids du repo gêne les contributeurs du site.

## Conséquences

- `build.py` : assemblage multi-fichiers + validation inter-fichiers (ids uniques globalement) ;
- migration one-shot des fichiers actuels (script, diff sémantiquement vide, PR dédiée) ;
- gabarit de pipeline documenté (lié aux missions de collecte, #17) ;
- CONTRIBUTING : « où va mon fichier » mis à jour.
