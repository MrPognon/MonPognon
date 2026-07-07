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

### Couverture actuelle — le baromètre

<!-- couverture:debut -->
| Périmètre | Montant | ✅ confirmé (en €) | 🟡 estimé | ❓ à réclamer |
|---|---|---|---|---|
| Dépenses des collectivités locales | 315,0 Md€ | **0,0 %** | 100,0 % | 2 nœud(s), dont 2 réclamé(s) |
| Recettes des collectivités locales | 315,0 Md€ | **0,0 %** | 100,0 % | 1 nœud(s), dont 1 réclamé(s) |
| Dépenses de l'État (PLF 2025, crédits de paiement) | 823,0 Md€ | **100,0 %** | 0,0 % | 2 nœud(s), dont 2 réclamé(s) |
| Recettes de l'État — budget général (PLF 2025) | 588,4 Md€ | **100,0 %** | 0,0 % | 0 nœud(s), dont 0 réclamé(s) |
| Dépenses de la Sécurité sociale (régimes de base + FSV) | 666,0 Md€ | **62,8 %** | 37,2 % | 2 nœud(s), dont 2 réclamé(s) |
| Recettes de la Sécurité sociale (régimes de base + FSV) | 644,4 Md€ | **100,0 %** | 0,0 % | 0 nœud(s), dont 0 réclamé(s) |

*Un euro est « confirmé » si le nœud le plus profond qui le porte l'est — la méthode complète est dans [`site/couverture.json`](site/couverture.json). Les périmètres ne s'additionnent pas (transferts entre administrations). Tableau régénéré par `build.py`.*
<!-- couverture:fin -->

## Un projet apolitique, celui du peuple français

Ce projet est **apolitique** et le restera _ad vitam æternam_. Il n'est, et ne sera **jamais**, le projet d'une seule personne ni d'un groupe de personnes : c'est le **projet du peuple français**. Il a simplement été initié pour montrer que nous, citoyens, avec la puissance technologique moderne, pouvons réaliser l'**agrégation qu'aucun gouvernement français n'a souhaité faire** — de manière claire, visible et publique, en un seul et unique endroit.

**Aucune affiliation — publique ou privée — n'est nécessaire, ni ne sera demandée ou acceptée.** De rares exceptions pourront être faites côté privé ; elles seront **toujours motivées et explicitées publiquement**, et concerneront pour l'essentiel le soutien à la **gestion technique et à l'infrastructure**, ou à la **recherche et l'exécution assistées par une ou plusieurs IA dont la gouvernance est, et sera, clairement établie**.

Sa neutralité est sa force : **le site montre les chiffres et donne à chaque citoyen les moyens de juger par lui-même** — il ne porte, lui, aucun jugement sur l'opportunité d'une dépense ou d'une recette. C'est précisément cette rigueur qui fait sa crédibilité.

## Voir le site

Ouvrez `site/index.html` dans un navigateur (ou activez GitHub Pages sur le dossier `site/`). Trois modes :

- **💸 Dépenses** — des 1 670 Md€ de dépenses publiques jusqu'aux actions budgétaires. L'**intégralité du PLF 2025** est intégrée jusqu'au niveau le plus fin de l'open data — budget général + CAS + CCF + BA, des missions jusqu'aux sous-actions, **chaque feuille ventilée par nature de dépense** (personnel, fonctionnement, investissement… — titres LOLF). Les comptes 2025 de la Sécurité sociale sont confirmés par branche (rapport CCSS).
- **💰 Recettes** — qui paie quoi : les 156 lignes de l'état A du PLF (chaque impôt, taxe, redevance, dividende), plus la Sécu et les collectivités.
- **🧾 Ma fiche de paie** — entrez votre brut, suivez chaque euro prélevé jusqu'à sa destination.

## Structure du dépôt

```
data/                    ← LA source de vérité (c'est ici qu'on contribue)
  etat/depenses.json       arbre des dépenses de l'État (PLF 2025, API data.economie)
  etat/recettes.json       les 156 lignes de recettes de l'état A
  secu/…                   comptes 2025 par branche (confirmés, rapport CCSS)
  collectivites/…          agrégats nationaux + fiches par commune (communes/<dept>/<insee>.json)
schema/noeud.schema.json ← format d'un nœud (documenté)
scripts/build.py         ← valide data/ et génère site/data.js
scripts/extract_plf.py   ← modèle d'extraction depuis l'API data.economie
site/                    ← site statique (D3, sans build front, hébergeable sur GitHub Pages)
.github/workflows/       ← CI : toute PR est validée (schéma, sources, cohérence des sommes)
```

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Les chantiers prioritaires sont listés dans les nœuds `a_completer` et `inconnu` de l'arbre lui-même — le site EST la todo-list.

Grands chantiers :

1. ~~Intégrer le PLF 2025 intégral puis le ventiler par nature~~ ✅ Fait (missions → sous-actions, chaque feuille ventilée par titre LOLF).
2. ~~Structurer les comptes de la Sécurité sociale par branche~~ ✅ Fait (rapport CCSS mai 2026, résultats 2025) — reste la ventilation fine de l'ONDAM (hôpital / ville / médico-social), voir le baromètre.
3. Brancher le sélecteur de commune sur l'API OFGL (fiche réelle recettes/dépenses par commune).
4. Documenter « qui perçoit » (opérateurs, universités, associations) et « qui paie » (ménages/entreprises, répartition territoriale) ligne par ligne.
5. Réclamer les données manquantes (nœuds ❓) via [madada.fr](https://madada.fr) et tracer les demandes ici.

## Design

Le site suit les **principes** du [Système de Design de l'État (DSFR)](https://www.systeme-de-design.gouv.fr/) — sobriété, contrastes RGAA, badges de statut, callouts sourcés — **sans réutiliser ses composants, sa palette « bleu France » ni la police Marianne** : leur usage est formellement réservé aux sites de l'État ([périmètre d'application](https://www.systeme-de-design.gouv.fr/version-courante/fr/premiers-pas/perimetre-d-application)), précisément pour qu'un site citoyen comme celui-ci ne puisse pas être confondu avec un site officiel. Il s'agit d'une **inspiration assumée, non d'une réutilisation** : aucune autorisation n'est donc requise ni sollicitée. Si le projet était un jour porté par une administration (ex. beta.gouv.fr), l'adoption du vrai DSFR se ferait sur agrément du SIG.

## Sources et licences

Toutes les données proviennent de sources officielles sous **Licence Ouverte 2.0 (Etalab)** sauf mention contraire, citées nœud par nœud avec date de consultation. Étude complète des sources disponibles : voir `docs/etude-donnees.md`.

Code sous licence **AGPL-3.0** (compatible avec OpenFisca/LexImpact ; les briques Urssaf `modele-social`/Publicodes sont MIT).
