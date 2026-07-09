# Gouvernance

> Ce document dit **qui décide quoi, et comment** — écrit avant d'en avoir besoin. Il est la traduction opérationnelle du manifeste du [README](README.md) : ce projet est apolitique, il appartient au peuple français, et sa gouvernance doit rendre ces promesses **vérifiables**.

## Les rôles

| Rôle | Qui | Ce qu'il peut faire | Comment on le devient |
|---|---|---|---|
| **Contributeur** | tout le monde | proposer des PRs (données, code, docs), ouvrir des issues, participer aux discussions | en contribuant — aucune autorisation à demander |
| **Contributeur de confiance** | contributeurs réguliers | relire les PRs de données de son périmètre (sa relecture compte comme revue) | proposé publiquement par un mainteneur après plusieurs PRs de qualité fusionnées |
| **Référent de périmètre** | spécialistes d'un sous-arbre (État, Sécu, collectivités, communes d'un territoire…) | valider les PRs de données de son périmètre ([`CODEOWNERS`](.github/CODEOWNERS)) | cooptation publique par les mainteneurs, sur historique de contributions |
| **Mainteneur** | responsables du projet | fusionner, approuver les domaines de sources ([tier 3](data-sources/domaines/approuves.json)), modérer, faire évoluer la gouvernance | cooptation à la majorité des mainteneurs en place, annoncée publiquement |

Aucun rôle ne se demande : tous se constatent, publiquement, sur les contributions.

## Comment se prennent les décisions

- **Structure, schéma, architecture** → un **ADR public** dans [`docs/adr/`](docs/adr/INDEX.md), débattu et acté dans sa PR. C'est déjà la pratique (5 ADRs).
- **Une donnée est contestée** → l'issue [« Contester une donnée »](.github/ISSUE_TEMPLATE/contester-une-donnee.md). Règle de fond : **une contestation sourcée est une contribution, pas une attaque.** Si deux sources officielles se contredisent, le site **affiche l'écart** (nœud et description factuelle des deux lectures) — on ne tranche jamais en coulisses.
- **Gouvernance et modération** → majorité des mainteneurs, décision et motif publiés dans l'issue concernée.
- Le reste — la vie courante — se décide **dans les issues et les PRs**, à ciel ouvert. Pas de canal privé de décision.

## Les règles de fusion

1. **Jamais d'auto-merge, jamais de commit direct sur `main`** (protection de branche active) ;
2. la **CI doit être verte** (`validate` obligatoire ; `sources` et `fond` éclairent la revue) ;
3. PR de **données** : une revue d'un mainteneur, d'un référent du périmètre, ou d'un contributeur de confiance ;
4. PR touchant **`schema/`, `scripts/build.py` ou `.github/`** (les fondations) : revue d'un mainteneur — et deux revues dès qu'il y aura plusieurs mainteneurs ;
5. les PRs générées par pipeline (masse) se relisent **par leur script et leur rapport**, pas ligne à ligne ([ADR-0002](docs/adr/ADR-0002-data-a-l-echelle.md)).

## La neutralité, opérationnellement

La règle d'or éditoriale — *documenter les flux, ne jamais juger de leur opportunité* — s'applique **aussi aux espaces de discussion** : on y débat des **sources, des périmètres et des méthodes**, pas de la légitimité politique d'une dépense ou d'une recette. Le militantisme, dans un sens comme dans l'autre, est **hors sujet ici** (pas illégitime ailleurs). Voir le [code de conduite](CODE_OF_CONDUCT.md).

**Modération** (par les mainteneurs) — ce qui est traité : le militantisme dans les contenus du projet, les attaques personnelles, la publication de données personnelles. Comment : gradué et **tracé publiquement** — rappel de la règle → masquage du contenu → blocage en dernier recours, chaque étape motivée dans le fil concerné.

## Ce qui protège le projet — y compris de ses mainteneurs

- **Tout est public** : données, sources, décisions, modération. Ce qui ne peut pas se dire publiquement n'a pas sa place ici.
- **Le fork est un droit** (licence AGPL-3.0) : si la gouvernance déraillait, n'importe qui peut repartir du dépôt complet, données et historique compris. Ce n'est pas une menace, c'est le garde-fou ultime — le projet n'est captable par personne, pas même par ses mainteneurs.
- **Trajectoire** : dès qu'il y a **au moins deux mainteneurs actifs**, le dépôt migre vers une **organisation GitHub** dédiée (sortir du compte personnel : bus factor et neutralité d'image). Ce document sera mis à jour à ce moment-là.

## En pratique, aujourd'hui

Le projet démarre : un seul mainteneur ([@MrPognon](https://github.com/MrPognon)), qui applique ce document et cherche activement à se faire remplacer aux postes ci-dessus. Les candidatures ne se posent pas : **contribuez, le reste suit.**
