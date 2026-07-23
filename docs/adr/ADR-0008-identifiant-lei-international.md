# ADR-0008 — Admettre le LEI comme identifiant de bénéficiaire au niveau P5

- **Statut : Accepté** (2026-07-23, décision du mainteneur)
- **Date : 2026-07-23**
- **Complète** : ADR-0006 (définition de P5 et du champ `identifiant`)

## Contexte

P5 — « bénéficiaire final nommé » — exige deux conditions (ADR-0006) : un **identifiant machine** et un **rattachement** à la ligne payeuse. L'identifiant existe pour qu'un euro ne soit pas seulement attribué à un *nom* — ambigu, invérifiable — mais à une **entité reliée à un registre public**.

Le `schema/noeud.schema.json` énumérait trois types d'identifiant : `SIREN`, `SIRET`, `RNA`. **Les trois sont des registres français.** Un bénéficiaire qui n'est pas une personne morale française ne pouvait donc, en l'état, jamais atteindre P5 — quelle que soit la certitude de son identité.

Ce n'est pas un cas marginal. L'annexe jaune « Effort financier de l'État en faveur des associations » (versements 2023), source des 112 722 bénéficiaires, verse à des organismes internationaux que les registres français ne couvrent pas. La source l'écrit elle-même : leur colonne `siren` porte **`"NR CHORUS"`** (non référencé dans Chorus) ou **`"0"`**.

**478 lignes, 1 078 M€, sont dans ce cas — et un seul bénéficiaire en porte 93 % :**

| Bénéficiaire | Programme | Montant | `siren` (source) |
|---|---|--:|---|
| **Association Internationale de Développement** (IDA — Banque mondiale) | 110 | **1 004,0 M€** | `NR CHORUS` |
| CICR, GCERF, IATA, Alliances Françaises… | divers | ~45 M€ | `NR` / `0` |
| Associations FR à dénomination tronquée | divers | ~30 M€ | `0` |

La contribution de la France à l'IDA — le guichet concessionnel de la Banque mondiale — est un euro public parfaitement identifiable, resté bloqué à P0 au seul motif que le vocabulaire d'identifiants du projet était **franco-français**.

## Décision

**Le `LEI` (Legal Entity Identifier, ISO 17442) devient un type d'identifiant admis au niveau P5, aux côtés de `SIREN`, `SIRET`, `RNA`.**

Le LEI est l'identifiant mondial des entités juridiques, tenu par la **GLEIF** (Global Legal Entity Identifier Foundation) et **vérifiable publiquement** (`api.gleif.org`). Pour une entité internationale, il est *plus* probant qu'un nom : il lève l'ambiguïté qu'un « CICR » ou un « IDA » saisi à la main ne lève pas.

### Ce qui rend le LEI honnête, et non une porte dérobée

Un `identifiant.type: "LEI"` n'est valide que si sa `valeur` **résout sur GLEIF** vers un enregistrement **actif** (`registrationStatus: ISSUED`) dont le nom légal correspond au bénéficiaire. La provenance — GLEIF, date de consultation, statut — est portée par le nœud, exactement comme un SIREN se réfère à SIRENE / l'Annuaire des entreprises. **Un identifiant reste une assertion vérifiable, jamais une étiquette libre.**

### Ce qu'on n'invente pas

Le principe demeure : **on n'ajoute jamais un identifiant que la source n'a pas et qu'on ne peut pas vérifier.** Un organisme sans SIREN *et* sans LEI GLEIF reste à P0. Admettre le LEI récupère les entités internationales **enregistrées** ; il ne blanchit pas les lignes réellement non identifiables.

## Ce que cet ADR ne fait PAS

**À énoncer sans détour — un identifiant plus permissif est précisément le genre d'ouverture dont il ne faut pas surestimer la portée.**

- **Il ne fait pas remonter les 478 lignes à P5.** Il rend éligibles celles qui ont un LEI GLEIF. Les ~30 M€ d'associations françaises à `siren: "0"` n'ont pas de LEI ; leur SIREN n'est retrouvable que par rapprochement de nom sur SIRENE — une mission de collecte distincte, avec son propre risque de faux appariement sur des noms coupés à 30 caractères, **hors** de cet ADR.
- **Il ne vérifie pas le LEI dans `build.py`.** Le build ne fait aucune I/O réseau. `collecter_p5()` accepte déjà tout `identifiant` non vide sans contrôler son type ; `valider_rattachements()` n'exige que `type` + `valeur`. Admettre le LEI est donc un changement de **schéma et de doctrine**, pas de code. La résolution GLEIF est une étape humaine, **sourcée sur le nœud** — comme l'est le sourçage d'un SIREN.
- **Il ne prouve pas que ce versement a atteint cette entité.** Le LEI atteste que le bénéficiaire est une personne morale enregistrée. Que *cet* euro lui soit allé reste attesté par le **rattachement** (la ligne payeuse) et la **source** (l'annexe jaune) — inchangés.
- **Il n'ouvre pas l'énumération.** `identifiant.type` reste une liste fermée : `LEI` s'y ajoute par cet ADR, pas un type arbitraire par une PR de données. C'est la même discipline que `BASES_COMPTABLES` (ADR-0007).

## Conséquences

- `schema/noeud.schema.json` : `identifiant.type` gagne `"LEI"`, et sa description distingue registres français (SIREN/SIRET/RNA) et LEI international.
- `data/etat/subventions/110.json` : le nœud IDA reçoit `identifiant: {type: "LEI", valeur: "P41R60HC414IWQA1XW02"}`, son nom complet rétabli (la source le tronquait à « Ass Internationale De Developpemen »), et une `description` portant la provenance GLEIF et le `NR CHORUS` de la source.
- **Effet mesuré (volet dépenses)** : P5 passe de **7,145 à 7,818 Md€** — soit **+0,673 Md€ d'univers**, égal aux 1 004 M€ de corpus reclassés × le ratio SEC de l'État (551,9 / 823,0 = 0,671). **P de 2,663 à 2,665** (+0,0016, conforme au taux de change d'ADR-0006 : 1 Md€ reclassé P3→P5 vaut +0,00160). **C est strictement inchangé** — un reclassement P5 ne touche jamais la largeur.
- Les autres organismes internationaux (CICR, GCERF, IATA…) deviennent éligibles sous la même règle ; sourcer leurs LEI un à un est un incrément ultérieur, **pas fait ici** (une PR, un sujet).

## Vérification

- Enregistrement GLEIF cité : LEI `P41R60HC414IWQA1XW02`, « International Development Association », Washington US-DC (siège du groupe Banque mondiale, 1818 H Street NW), entité `ACTIVE`, enregistrement `ISSUED`, prochaine échéance 2027-03-22. Le seul homonyme GLEIF est une entité néerlandaise *annulée* (`ANNULLED`, 2018) — écartée sans ambiguïté.
- `build.py --check` : `exit 0`, aucun nouvel avertissement.
- P5 recalculé par le vrai `indice_cp()` : 7,145 → 7,818 Md€ ; C inchangé (les deux mesurés avant/après l'ajout du seul identifiant).

## Alternatives rejetées

- **Inventer un SIREN, ou rapprocher l'IDA d'un registre français.** Rejeté : viole la règle d'or. Un organisme international n'a pas de SIREN par construction ; en fabriquer un serait un mensonge machine.
- **Admettre le nom seul à P5.** Rejeté : un nom est ambigu et invérifiable — c'est exactement ce contre quoi l'exigence d'identifiant existe. « Cete Apave Ci » l'illustre.
- **Laisser l'IDA à P0.** Rejeté : un bénéficiaire nommé, doté d'un identifiant machine mondial et vérifiable, est précisément ce que P5 mesure. Le refuser parce que l'identifiant n'est pas français, ce serait sous-estimer la profondeur réelle de ~1 Md€ et inscrire un biais franco-centré dans l'axe P.
