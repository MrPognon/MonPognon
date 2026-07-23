# ADR-0009 — Fermer le recouvrement inter-`bloc_univers`

- **Statut : Accepté** (2026-07-23, décision du mainteneur)
- **Date : 2026-07-23**
- **Complète** : ADR-0007, section « Ce que ce verrou ne fait pas », point 4

## Contexte

ADR-0007 a rendu mécanique la règle du référentiel homogène — mais son propre bilan d'honnêteté énonçait quatre attaques qu'il ne fermait **pas**. La quatrième :

> « Les six règles sont TOUTES intra-bloc : rien ne détecte qu'un même euro soit compté dans DEUX blocs. […] L'arbre porte déjà `secu.depenses.maladie.hopital` = 109,4 Md€ (« Établissements de santé (ONDAM) »), en base CCSS sous `ASSO.regimes`. Un corpus hospitalier étiqueté CCSS et rattaché à `ASSO.odass` réexprimerait ces mêmes euros, satisferait A→F sans une erreur, et gonflerait C d'un montant **faux** — pas seulement nul. »

C'est la **seule** attaque connue qui gonfle C d'un montant faux plutôt que nul : les blocs sans référentiel comptent zéro, mais un recouvrement ajoute des euros réels au mauvais endroit. Rien ne le voyait.

## Décision

**`build.py` refuse qu'un même montant confirmé soit compté sous deux `bloc_univers` distincts.**

`valider_recouvrement_blocs()` construit l'empreinte de chaque montant `confirme` > 0 — **(montant à l'euro près, année, volet)** — et signale toute empreinte portée par **deux blocs distincts**.

Trois discriminants, chacun établi par mesure sur le corpus réel (1,44 M de nœuds, 23/07/2026), sans lesquels le signal serait noyé sous les coïncidences :

| Discriminant | Ce qu'il retire | Pourquoi |
|---|---:|---|
| **Même volet** | 14 | C se calcule par volet. Les seules collisions cross-comptabilité du corpus sont des emprunts (recette d'un département) au même montant rond qu'une dépense de l'État — deux volets, jamais comptés ensemble. |
| **Hors échelons de collectivités** | 9 293 | Communes, départements, régions, syndicats, ODAL sont des personnes morales **séparées**, réconciliées une à une par code INSEE : deux d'entre elles au même montant, c'est une coïncidence, jamais le même euro. |
| **Seuil 100 M€** (erreur vs avertissement) | — | Au-delà, un même chiffre précis sous deux comptabilités n'est pas une coïncidence : erreur bloquante. En deçà, avertissement — une coïncidence reste plausible. |

Après ces trois discriminants, le corpus actuel présente **zéro** collision : le verrou ne bloque rien de légitime aujourd'hui, et attrape la réexpression de l'hôpital ONDAM (vérifié).

`ECHELONS_COLLECTIVITES` est une liste **fermée**, comme `BASES_COMPTABLES` (ADR-0007) : y ajouter un échelon est une décision de code, jamais un effet de bord d'une PR de données.

## Ce que ce verrou ne fait PAS

**À énoncer sans détour — répéter la surpromesse qu'ADR-0007 corrige serait pire que la faille.**

Le verrou compare des **montants**. Il ne relit aucune source et ne comprend aucun périmètre.

1. **Une réexpression aux montants différents lui échappe.** Réexprimer l'hôpital ONDAM non au montant exact mais ventilé en dix lignes hospitalières distinctes — aucune n'égalant le montant d'origine — ne déclenche aucune collision. Le verrou attrape la **copie** et la réexpression naïve à l'agrégat, pas le blanchiment par re-granularisation.
2. **Sous 100 M€, il avertit sans bloquer.** Un recouvrement fractionné en tranches sous le seuil passe en avertissements — visibles au diff, non bloquants. Le fractionner assez pour rester discret demande des dizaines de nœuds, eux-mêmes visibles.
3. **Il ne dit pas QUEL bloc est le bon.** Il signale que deux blocs se disputent les mêmes euros ; c'est à l'humain de trancher lequel les porte légitimement. Un recouvrement révèle souvent un vrai défaut de modélisation, pas seulement une attaque — les hôpitaux publics relèvent en réalité de S13142/ODASS au sens INSEE, pas des régimes.
4. **L'autre contrôle ouvert d'ADR-0007 reste ouvert.** Re-vérifier les `total_eur` des dix référentiels à leur source — le pendant, côté dénominateur, de ce que `verify-fond.yml` fait pour les montants de l'arbre — n'est **pas** fait ici. C'est un chantier distinct (resolvers OFGL/INSEE), et il ne faut pas prétendre qu'il l'est.

Ce que le verrou change malgré tout : le recouvrement à l'agrégat cesse d'être une **omission invisible** pour devenir une **écriture explicite** — un même montant, sous deux blocs — refusée par le build ou signalée au diff. La relecture humaine reste **nécessaire** ; elle sait désormais où regarder.

## Conséquences

- `build.py` : `ECHELONS_COLLECTIVITES`, `SEUIL_RECOUVREMENT`, `volet_du_noeud()`, `valider_recouvrement_blocs()`, appelée dans `main()` après `valider_sur_rattachement()`.
- **Aucune donnée touchée. C et P strictement inchangés** : ce verrou ne change pas ce que le site mesure, il empêche de le mesurer faux (même principe qu'ADR-0007).
- Le corpus actuel passe sans une erreur ni un avertissement de recouvrement.

## Vérification

| Cas | Verdict |
|---|---|
| Corpus réel au 23/07/2026 (1,44 M nœuds) | `exit 0`, zéro recouvrement |
| Hôpital ONDAM (109,4 Md€) réexprimé sous `ASSO.odass`, même volet | **`exit 1`** — les deux blocs nommés, le nœud coupable cité |
| Le fichier d'attaque retiré | `exit 0` |

L'attaque rejouée est exactement celle qu'ADR-0007 décrivait comme non fermée.

## Alternatives rejetées

- **Empreinte incluant le `producteur`.** Rejeté : une réexpression change de source (ONDAM/CCSS → ATIH), donc de producteur. L'empreinte doit être (montant, année, volet) seule pour suivre le même euro d'une comptabilité à l'autre.
- **Un simple seuil de montant, sans les autres discriminants.** Rejeté : mesuré, il laisse des dizaines de collisions rondes entre collectivités à ≥ 1 M€ — du bruit qui aurait entraîné à ignorer le signal, exactement le défaut que le faux positif de `build.py` illustrait (corrigé en #84).
- **Un contrôle sémantique de périmètre** (déclarer les sous-secteurs SEC de chaque bloc et vérifier leur disjonction). Souhaitable, hors d'atteinte mécanique : dire si des euros hospitaliers relèvent de S13141 ou S13142 est un jugement de source, pas une comparaison de chaînes. Le verrou signale le conflit ; l'analyste le tranche.
