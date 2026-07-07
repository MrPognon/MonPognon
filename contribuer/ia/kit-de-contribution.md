# Kit de contribution assistée par IA

> Ce document est le **contexte partagé** que ton assistant IA (quel qu'il soit) doit connaître pour t'aider à contribuer. Les [prompts prêts à coller](prompts/) s'appuient dessus. Tu peux aussi le donner tel quel à ton IA.

## Ce que fait le projet, en une phrase

« Où va l'argent public ? » rassemble, en un seul endroit et sous forme d'arbre, **d'où vient et où va chaque euro public en France**, avec pour **chaque chiffre sa source officielle**.

## La règle d'or (non négociable)

> **Tout chiffre a une source officielle : URL + producteur + date de consultation + millésime (`annee`).** On n'invente JAMAIS un chiffre « de tête », on n'arrondit pas sans le dire, on ne mélange pas les années. Un chiffre sans source est refusé, même s'il est juste.

Si la donnée **n'existe pas publiquement**, ce n'est pas un échec : on crée un nœud `inconnu` qui dit *quoi* manque et *qui* contacter. **Cartographier l'ombre a autant de valeur qu'un chiffre confirmé.**

## Neutralité

Le projet **documente les flux, il ne juge jamais leur opportunité**. Les textes (`description`) restent factuels : pas de militantisme, pas d'opinion. C'est la condition de sa crédibilité et de son apolitisme.

## Anatomie d'un nœud (le format à produire)

Les données vivent dans des fichiers JSON sous `data/` : un arbre par fichier, chaque nœud a des `enfants`. Format complet : [`schema/noeud.schema.json`](../../schema/noeud.schema.json).

| Champ | Obligatoire | Rôle |
|---|:--:|---|
| `id` | ✅ | identifiant unique hiérarchique, ex. `etat.depenses.RS.150` (minuscules, segments séparés par des points) |
| `label` | ✅ | libellé lisible (≥ 3 caractères) |
| `statut` | ✅ | `confirme` · `estime` · `inconnu` |
| `source` | ✅ | objet `{ nom, url, producteur, consulte_le }` (+ `licence`, `maj` recommandés) |
| `enfants` | ✅ | tableau de sous-nœuds (peut être `[]`) |
| `montant` | | en euros — décimales acceptées, ex. les centimes des comptes OFGL (`null` si inconnu) |
| `annee` | | millésime de la donnée (entier) |
| `description` | | contexte factuel ; **obligatoire de fait pour un `estime`** (explique la méthode) |
| `inconnu` | | pour un nœud `inconnu` : `{ quoi, contact, url }` |

### Les trois statuts

- **`confirme`** — le montant est **copié tel quel** de la source officielle. Aucun calcul.
- **`estime`** — ordre de grandeur, calcul dérivé ou source secondaire → explique la méthode dans `description`.
- **`inconnu`** — la donnée n'existe pas publiquement → bloc `inconnu` avec `quoi` (ce qui manque) et `contact` (l'administration à solliciter), `url` = lien d'une éventuelle demande [madada.fr](https://madada.fr).

### Exemple de nœud `confirme`

```json
{
  "id": "etat.depenses.DA.146",
  "label": "Programme 146 — Équipement des forces",
  "montant": 18500000000,
  "annee": 2025,
  "statut": "confirme",
  "description": "Optionnel : contexte factuel utile au citoyen.",
  "source": {
    "nom": "PLF 2025 — dépenses selon destination",
    "url": "https://data.economie.gouv.fr/explore/dataset/plf25-depenses-2025-selon-destination/",
    "producteur": "Direction du budget",
    "licence": "Licence Ouverte 2.0",
    "consulte_le": "2026-07-07",
    "maj": "2025-10-10"
  },
  "enfants": []
}
```

### Exemple de nœud `inconnu`

```json
{
  "id": "coll.depenses.communes.macommune.detail",
  "label": "Détail des dépenses de ma commune (non publié en open data)",
  "montant": null,
  "statut": "inconnu",
  "source": {
    "nom": "Recherche OFGL / balance communale",
    "url": "https://www.ofgl.fr/",
    "producteur": "OFGL",
    "consulte_le": "2026-07-07"
  },
  "inconnu": {
    "quoi": "Ventilation fine des dépenses de fonctionnement de la commune X",
    "contact": "Mairie de X — service financier / secrétariat de mairie",
    "url": null
  },
  "enfants": []
}
```

## Où placer ton nœud

L'`id` donne le fichier et l'emplacement :

| L'id commence par… | Fichier |
|---|---|
| `etat.depenses.` | `data/etat/depenses.json` |
| `etat.recettes.` | `data/etat/recettes.json` |
| `secu.` | `data/secu/depenses.json` ou `recettes.json` |
| `coll.` | `data/collectivites/depenses.json` ou `recettes.json` (agrégats nationaux uniquement) |
| `commune.<insee>.` | `data/collectivites/communes/<n° département>/<code INSEE>.json` — la fiche de TA commune (voir ci-dessous) |

Un nouveau nœud s'ajoute dans le tableau `enfants` de son **parent logique** (ex. une action se range sous son programme). Si tu ne sais pas où, mets-le au niveau le plus proche et **dis-le dans la PR** — un mainteneur t'aidera à le ranger.

### Le budget de ta commune : un fichier dédié (ADR-0004)

Une commune = **un fichier**, jamais un nœud de l'arbre national (sinon ses recettes seraient comptées deux fois). Structure imposée :

- fichier : `data/collectivites/communes/<n° département>/<code INSEE>.json` (ex. `45/45082.json`) ;
- nœud racine `commune.<insee>` avec **`montant: null`** (les dépenses et les recettes ne s'additionnent pas) ;
- deux enfants : `commune.<insee>.depenses` et `commune.<insee>.recettes`, chacun avec son arbre sourcé (OFGL, balances DGFiP…).

**Dans le navigateur** : sur GitHub, bouton **« Add file » → « Create new file »**, tape le chemin complet (`data/collectivites/communes/45/45082.json` — GitHub crée les dossiers tout seul), colle le JSON entier, puis « Commit changes » → « Propose changes ». Exemple fondateur à imiter : la fiche `45082` (Châteauneuf-sur-Loire).

## Cohérence des sommes

La validation tolère un écart de **± 2 %** entre un parent et la somme de ses enfants. Si ça dépasse, ce n'est pas à contourner : signale-le dans la PR (souvent un périmètre ou un millésime à préciser).

## Pièges des APIs officielles (pour l'IA qui va chercher la donnée)

Appris sur le terrain — ils font perdre du temps à toutes les IA :

- **ODS / data.economie** : URL-encoder les parenthèses et les quotes des query params (`select=sum%28credit_de_paiement%29`), sinon **400 silencieux**. Gros volumes : `/exports/json` + compression.
- **OFGL** (`ofgl-base-communes`, comptes des communes) : le champ `exer` (exercice) est une **date**, pas un texte — filtrer avec `where=year(exer)=2024`, jamais `exer="2024"` (erreur `IncompatibleTypesInComparisonFilter`). Penser à filtrer aussi `type_de_budget="Budget principal"` pour ne pas mélanger budgets annexes et principal.
- **Balances comptables DGFiP** (`balances-comptables-des-communes-en-<année>` sur data.economie) : le niveau **sous** les agrégats OFGL — chaque **compte comptable M57/M14** de chaque commune (ex. compte `20422` = subventions d'équipement aux personnes de droit privé). Trois pièges : ① `obnetdeb`/`obnetcre` = **flux de l'exercice** (mandaté/titré net), alors que `sd`/`sc` = **stocks cumulés au bilan** — ne jamais les confondre ; ② filtrer `cbudg="1"` (budget principal) ; ③ les agrégats OFGL se recalculent depuis ces comptes (bonne vérification croisée : ex. « Subventions d'équipement versées » = somme des `obnetdeb` des comptes `204x`).
- **Le nominatif (qui a reçu, qui a payé)** n'est PAS dans les balances : subventions attribuées → obligation de publication seulement au-delà de 23 000 € (schéma SCDL) ; marchés publics → DECP. Beaucoup de communes ne publient rien : c'est alors un **nœud `inconnu`** avec la mairie en contact (délibérations du conseil municipal) — une contribution de pleine valeur.
- **Hygiène des liens (vérifiée automatiquement en CI)** : `source.url` doit être en **HTTPS**, jamais un raccourcisseur (bit.ly…), jamais une adresse IP. Les domaines officiels nationaux et les domaines approuvés (`data-sources/domaines/`) passent seuls ; un domaine inconnu (ex. le site d'une mairie) n'est **pas bloqué** mais déclenche une revue humaine ciblée — justifie-le dans la PR.
- **Date de mise à jour d'un jeu ODS** (pour `source.maj`) : `GET /api/explore/v2.1/catalog/datasets/<id>` → `metas.default.modified`.
- **Recettes d'une commune** : elles vont dans la **fiche de la commune** (`commune.<insee>.recettes` — voir « Le budget de ta commune » ci-dessus), jamais dans l'arbre national des recettes, qui est ventilé par nature (décision ADR-0004).

## Proposer ta contribution — SANS rien connaître à git (dans le navigateur)

1. Va sur le fichier concerné sur GitHub, ex. **https://github.com/MrPognon/MonPognon/blob/main/data/etat/depenses.json**
2. Clique sur l'icône **crayon ✏️ (« Edit this file »)** en haut à droite. GitHub crée automatiquement ta copie (fork) — accepte.
3. **Colle** le JSON produit par ton IA au bon endroit (dans les `enfants` du parent). Respecte les virgules.
4. En bas, clique **« Commit changes… »** puis **« Propose changes »** : ça ouvre une **pull request** avec le modèle à remplir (source, méthode, ce que tu n'as pas pu vérifier).
5. C'est tout. La validation automatique et un mainteneur prennent le relais. Zéro terminal, zéro git.

> 💡 Le fichier `site/data.js` (l'affichage) est **régénéré par un mainteneur** à la fusion — tu n'as pas à t'en occuper. Tu ne touches qu'aux fichiers de `data/`.

## Ce que tu dois donner à ton IA

- **Ta source** : le lien officiel (data.gouv, un PDF de rapport, le site d'une collectivité…) + la date où tu l'as consultée.
- **Le(s) chiffre(s)** et à quoi ils correspondent (l'intitulé exact, l'année).
- **Où** ça se range si tu le sais (sinon l'IA proposera).

L'IA s'occupe de produire le JSON valide et de te rappeler les étapes ci-dessus.
