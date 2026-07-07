# ADR-0001 — Les flux croisés comme donnée : graphe de flux, arbres en vues

- **Statut : Accepté** (2026-07-07, validé dans la PR #20)
- **Date : 2026-07-07**

## Contexte

Le modèle de données actuel est un **arbre strict** (un nœud, des enfants, un montant). Il représente bien la décomposition d'un budget, mais mal la réalité des finances publiques, qui est faite de **flux croisés** :

- la TVA se partage entre État, Sécurité sociale et collectivités (fractions affectées) ;
- l'État verse aux collectivités des dotations (DGF…) et des prélèvements sur recettes ;
- la Sécu reçoit cotisations, CSG, TVA affectée, taxes, compensations — le circuit recette → branche n'est **pas bijectif** (règle déjà actée dans CLAUDE.md : nœuds « transferts » explicites).

L'ambition du projet — suivre « ce qui descend de l'État et ce qui remonte par capillarité » — est précisément la partie que l'arbre ne sait pas dire. C'est aussi la visualisation la plus attendue (Sankey) et la moins bien couverte par les projets existants.

## Options

**A. Statu quo** — tout-arbre, avec des nœuds « transferts » par convention.
- ✅ simple, déjà en place ; ❌ les transferts sont dupliqués dans plusieurs arbres sans lien formel entre eux, double-comptes invérifiables par la machine, pas de Sankey possible sérieusement.

**B. Graphe de flux comme donnée de première classe, arbres conservés comme vues** *(recommandée)*
- Introduire `data/flux/*.json` : des **liens** typés `{source_id, cible_id, montant, annee, type, statut, source}` entre nœuds existants des arbres — mêmes règles de sourcing que les nœuds, nouveau `schema/flux.schema.json`, validation dans `build.py` (le montant d'un flux doit être cohérent avec les nœuds qu'il relie).
- Les arbres actuels **ne changent pas** (rétro-compatible) ; le Sankey et les contrôles de double-compte se construisent sur les flux.
- ✅ incrémental, ne casse rien, machine-vérifiable ; ❌ deuxième schéma à maintenir, risque de divergence arbre/flux (mitigé par la validation croisée).

**C. Tout-graphe** — remplacer les arbres par un graphe unique dont on projette des arbres.
- ✅ conceptuellement pur ; ❌ migration lourde de 1 400 nœuds, rupture des contributions en cours, complexité d'édition pour les contributeurs non techniques (l'arbre JSON lisible est un atout majeur).

## Décision proposée

**Option B.** L'arbre reste le format de contribution (lisible, éditable par tous) ; le graphe de flux capture les relations croisées, en commençant petit : les 4-5 grands transferts (TVA affectée, DGF, prélèvements sur recettes UE/collectivités, compensations Sécu), tous `estime` au départ, raffinés ensuite.

## Conséquences

- Nouveau `schema/flux.schema.json` + validation croisée dans `build.py` (les extrémités existent, cohérence des montants) ;
- le baromètre de couverture (#15) devra neutraliser les doubles comptes **via les flux** (méthode explicite plutôt qu'heuristique) ;
- la lentille Sankey (#18) devient constructible ;
- CONTRIBUTING/kit IA : documenter quand créer un flux plutôt qu'un nœud.
