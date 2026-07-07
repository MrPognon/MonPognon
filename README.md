# 🌳 Où va l'argent public ?

> **⚠️ Ce site n'était, n'est, et ne sera _jamais_ affilié — directement ou indirectement — à un gouvernement et/ou à un parti politique, passé, présent ou futur.**
> Ce site est **objectif et apolitique**, et ces volontés ne seront jamais remises en question.

Site open source et collaboratif pour comprendre **d'où vient et où va chaque euro public en France** : État, Sécurité sociale, collectivités — depuis votre fiche de paie jusqu'à l'action budgétaire la plus fine.

**Principe fondateur : l'incomplétude est assumée et visible.** Chaque nœud de l'arbre porte un statut :

| Statut | Signification |
|---|---|
| ✅ `confirme` | Extrait tel quel d'une source officielle (URL + date de consultation + licence) |
| 🟡 `estime` | Ordre de grandeur documenté, à raffiner |
| ❓ `inconnu` | La donnée **n'existe pas publiquement** — le nœud indique *qui contacter* et comment la réclamer (CADA / madada.fr) |

La communauté fait grandir l'arbre par pull requests : chaque contribution doit être **sourcée et datée** (validation automatique en CI).

## Un projet apolitique, celui du peuple français

Ce projet est **apolitique** et le restera _ad vitam æternam_. Il n'est, et ne sera **jamais**, le projet d'une seule personne ni d'un groupe de personnes : c'est le **projet du peuple français**. Il a simplement été initié pour montrer que nous, citoyens, avec la puissance technologique moderne, pouvons réaliser l'**agrégation qu'aucun gouvernement français n'a souhaité faire** — de manière claire, visible et publique, en un seul et unique endroit.

**Aucune affiliation — publique ou privée — n'est nécessaire, ni ne sera demandée ou acceptée.** De rares exceptions pourront être faites côté privé ; elles seront **toujours motivées et explicitées publiquement**, et concerneront pour l'essentiel le soutien à la **gestion technique et à l'infrastructure**, ou à la **recherche et l'exécution assistées par une ou plusieurs IA dont la gouvernance est, et sera, clairement établie**.

Sa neutralité est sa force : **le site montre les chiffres et donne à chaque citoyen les moyens de juger par lui-même** — il ne porte, lui, aucun jugement sur l'opportunité d'une dépense ou d'une recette. C'est précisément cette rigueur qui fait sa crédibilité.

## Voir le site

Ouvrez `site/index.html` dans un navigateur (ou activez GitHub Pages sur le dossier `site/`). Trois modes :

- **💸 Dépenses** — des 1 670 Md€ de dépenses publiques jusqu'aux actions budgétaires. L'**intégralité du PLF 2025** est intégrée jusqu'au niveau le plus fin de l'open data — budget général + CAS + CCF + BA, des missions jusqu'aux sous-actions (~1 200 nœuds, tout `confirme`). Prochain raffinement : ventiler chaque action par nature (personnel, fonctionnement, investissement).
- **💰 Recettes** — qui paie quoi : les 156 lignes de l'état A du PLF (chaque impôt, taxe, redevance, dividende), plus la Sécu et les collectivités.
- **🧾 Ma fiche de paie** — entrez votre brut, suivez chaque euro prélevé jusqu'à sa destination.

## Structure du dépôt

```
data/                    ← LA source de vérité (c'est ici qu'on contribue)
  etat/depenses.json       arbre des dépenses de l'État (PLF 2025, API data.economie)
  etat/recettes.json       les 156 lignes de recettes de l'état A
  secu/…  collectivites/…  ordres de grandeur à raffiner (statut "estime")
schema/noeud.schema.json ← format d'un nœud (documenté)
scripts/build.py         ← valide data/ et génère site/data.js
scripts/extract_plf.py   ← modèle d'extraction depuis l'API data.economie
site/                    ← site statique (D3, sans build front, hébergeable sur GitHub Pages)
.github/workflows/       ← CI : toute PR est validée (schéma, sources, cohérence des sommes)
```

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Les chantiers prioritaires sont listés dans les nœuds `a_completer` et `inconnu` de l'arbre lui-même — le site EST la todo-list.

Grands chantiers :

1. ~~Intégrer programmes → actions pour les 33 missions restantes~~ ✅ Fait : l'intégralité du PLF 2025 est intégrée (budget général + CAS + CCF + BA, jusqu'aux sous-actions — 1 200 nœuds). Prochain raffinement : ventiler chaque action par **nature** (personnel, fonctionnement, investissement — champs `titre`/`categorie` déjà présents dans le jeu source).
2. Structurer les comptes de la Sécurité sociale (rapports CCSS et annexe 3 PLFSS, PDF → JSON).
3. Brancher le sélecteur de commune sur l'API OFGL (fiche réelle recettes/dépenses par commune).
4. Documenter « qui perçoit » (opérateurs, universités, associations) et « qui paie » (ménages/entreprises, répartition territoriale) ligne par ligne.
5. Réclamer les données manquantes (nœuds ❓) via [madada.fr](https://madada.fr) et tracer les demandes ici.

## Design

Le site suit les **principes** du [Système de Design de l'État (DSFR)](https://www.systeme-de-design.gouv.fr/) — sobriété, contrastes RGAA, badges de statut, callouts sourcés — **sans réutiliser ses composants, sa palette « bleu France » ni la police Marianne** : leur usage est formellement réservé aux sites de l'État ([périmètre d'application](https://www.systeme-de-design.gouv.fr/version-courante/fr/premiers-pas/perimetre-d-application)), précisément pour qu'un site citoyen comme celui-ci ne puisse pas être confondu avec un site officiel. Il s'agit d'une **inspiration assumée, non d'une réutilisation** : aucune autorisation n'est donc requise ni sollicitée. Si le projet était un jour porté par une administration (ex. beta.gouv.fr), l'adoption du vrai DSFR se ferait sur agrément du SIG.

## Sources et licences

Toutes les données proviennent de sources officielles sous **Licence Ouverte 2.0 (Etalab)** sauf mention contraire, citées nœud par nœud avec date de consultation. Étude complète des sources disponibles : voir `docs/etude-donnees.md`.

Code sous licence **AGPL-3.0** (compatible avec OpenFisca/LexImpact ; les briques Urssaf `modele-social`/Publicodes sont MIT).
