# Architecture Decision Records

Les décisions structurantes du projet sont documentées ici, **publiquement**, au format ADR : contexte → options → décision → conséquences. Une décision se prend dans la PR qui introduit ou modifie l'ADR (statuts : *Proposé* → *Accepté* / *Refusé* / *Remplacé par ADR-XXXX*).

Quand écrire un ADR : changement du modèle de données ou du schéma, nouveau pattern d'architecture, nouvelle dépendance, choix engageant l'échelle ou la gouvernance technique.

| # | Titre | Statut | Date |
|---|---|---|---|
| [ADR-0001](ADR-0001-graphe-de-flux.md) | Les flux croisés comme donnée : graphe de flux, arbres en vues | Accepté | 2026-07-07 |
| [ADR-0002](ADR-0002-data-a-l-echelle.md) | Stratégie data à l'échelle : fichiers découpés, pipelines pour la masse | Accepté | 2026-07-07 |
| [ADR-0003](ADR-0003-axe-temps.md) | L'axe temps : millésimes successifs et voté vs exécuté | Accepté | 2026-07-07 |
| [ADR-0004](ADR-0004-fiches-communales.md) | Les fiches communales vivent hors de l'arbre national | Accepté | 2026-07-07 |
| [ADR-0005](ADR-0005-heritage-source.md) | Héritage de la source parent → enfants, au niveau du champ | Accepté | 2026-07-07 |
| [ADR-0006](ADR-0006-mesure-de-completion.md) | Mesurer la complétion contre l'univers réel : l'indice C·P | Accepté | 2026-07-20 |
