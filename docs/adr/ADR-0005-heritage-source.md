# ADR-0005 — Héritage de la source parent → enfants, au niveau du champ

- **Statut : Accepté** (2026-07-07, chantier lancé par le mainteneur — issue #22)
- **Date : 2026-07-07**

## Contexte

Le schéma exigeait une `source` **complète sur chaque nœud**. Constats de terrain :

- la fiche d'une commune (27 nœuds issus du même jeu OFGL) répète ~6 lignes de source par nœud — gros blocs intimidants pour les contributeurs, diffs illisibles, fichiers gonflés (~40 % du volume) ;
- à l'échelle des 101 départements (mission #17), la répétition coûterait des dizaines de Mo pour zéro information ;
- MAIS l'héritage « tout ou rien » ne suffirait pas : les enfants diffèrent souvent du parent par **un seul champ** (`nom` porte l'agrégat ou la page citée), les autres champs (url, producteur, licence, dates) étant identiques.

## Décision

**L'héritage se fait champ par champ, en descendant l'arbre :**

1. un nœud **sans** champ `source` hérite de la source **résolue** de son parent, entièrement ;
2. un nœud avec une source **partielle** (ex. `{"nom": "…, agrégat « X »"}`) déclare ce qui diffère et hérite des champs manquants ;
3. la **racine de chaque fichier** doit porter une source complète (`nom`, `url`, `producteur`, `consulte_le`) — c'est l'ancre de l'héritage ;
4. la résolution est faite par `build.py` **à la génération** : chaque nœud de `site/data.js` et des fragments porte sa source complète — **le site et les consommateurs ne changent pas**, la garantie légale (Licence Ouverte 2.0 : mention de source nœud par nœud) est inchangée ;
5. la validation s'applique **après résolution** : tout nœud doit avoir une source complète, sinon erreur ;
6. `python3 scripts/build.py --show <id>` affiche un nœud avec sa source résolue (vérification en revue sans lire les parents).

## Ce qui ne change pas

Le sens du champ `source`, la règle d'or, les statuts, la CI de fond (#12 — le bot résout l'héritage avant de re-vérifier), le rendu du site.

## Rejeté

- **Statu quo** (répétition intégrale) : ne passe pas l'échelle.
- **Registre de sources nommées** (`"source": "@ofgl-2024"` + table) : indirection nouvelle pour les contributeurs, gain marginal par rapport à l'héritage par champ.
- **Héritage tout-ou-rien** : ne gagne rien dès que `nom` précise l'agrégat/la page (cas majoritaire).

## Conséquences

- `build.py` : résolution descendante (`{**source_parent_resolue, **source_declaree}`) avant validation ; `--show` ;
- `scripts/verifiers/fond.py` : même résolution avant vérification ;
- `schema/noeud.schema.json` : `source` optionnelle (l'exigence racine + post-résolution est portée par le validateur) ;
- **migration one-shot** (`scripts/pipelines/alleger_sources.py`, rejouable) : retire des fichiers `data/` chaque champ de source égal au champ résolu du parent — **critère d'or : les fichiers générés sont identiques octet pour octet avant/après** ;
- kit, prompts et CONTRIBUTING : exemples raccourcis, mécanisme expliqué ;
- risque « héritage silencieux erroné » (enfant d'une autre source qui oublie de la déclarer) : mitigé par la revue, le bot #12, et `--show`.
