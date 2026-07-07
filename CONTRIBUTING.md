# Contribuer

Merci ! Ce projet grandit uniquement par contributions sourcées. Aucune connaissance en développement n'est nécessaire pour contribuer aux données : ce sont des fichiers JSON lisibles.

## 🤖 Le plus simple : contribuer avec l'aide d'une IA (sans rien connaître à l'informatique)

Tu as trouvé une information intéressante (le budget de ta commune, une ligne de dépense, un rapport…) et tu veux l'ajouter ? **Ton assistant IA fait le travail technique, toi tu fournis la source.** N'importe quel modèle convient (ChatGPT, Claude, Gemini, Perplexity, Le Chat, un LLM local…).

1. **Rassemble ta source officielle** : le lien, le chiffre, l'année, la date de consultation.
2. **Colle le prompt prêt** de ton IA (→ [`contribuer/ia/`](contribuer/ia/README.md)) et ajoute ton info : l'IA te rend un bloc **JSON** et te dit quel fichier modifier.
3. **Propose la modif dans le navigateur** : sur GitHub, bouton **✏️ Edit** du fichier → colle → **Propose changes**. La pull request s'ouvre toute seule. **Zéro terminal, zéro git.**

👉 **Tout est là : [`contribuer/ia/`](contribuer/ia/README.md)** (prompts par modèle + [kit de contribution](contribuer/ia/kit-de-contribution.md)). Assistants de code : voir [`AGENTS.md`](AGENTS.md), [`GEMINI.md`](GEMINI.md), [`CLAUDE.md`](CLAUDE.md).

Le reste de cette page décrit la contribution « à la main » — utile pour comprendre le format, que tu passes par une IA ou non.

## La règle d'or

> **Tout chiffre doit avoir une source officielle, une URL, une date de consultation et un millésime.** Un chiffre sans source sera refusé, même s'il est juste.

## Ajouter ou préciser un nœud

1. Trouvez le fichier concerné dans `data/` (l'`id` du nœud, visible sur le site, donne le chemin : `etat.depenses.RS.150` → `data/etat/depenses.json`).
2. Éditez directement sur GitHub (bouton ✏️) ou clonez le dépôt.
3. Respectez le format d'un nœud (`schema/noeud.schema.json`) :

```json
{
  "id": "etat.depenses.DA.146",
  "label": "Programme 146 — Équipement des forces",
  "montant": 18500000000,
  "annee": 2025,
  "statut": "confirme",
  "description": "Optionnel : contexte utile au citoyen.",
  "source": {
    "nom": "PLF 2025 — dépenses selon destination",
    "url": "https://data.economie.gouv.fr/explore/dataset/plf25-depenses-2025-selon-destination/",
    "producteur": "Direction du Budget",
    "licence": "Licence Ouverte 2.0",
    "consulte_le": "2026-07-07"
  },
  "enfants": []
}
```

4. Choisissez le bon `statut` :
   - `confirme` : le montant est extrait tel quel de la source (copie exacte, pas de calcul « de tête »).
   - `estime` : ordre de grandeur, calcul dérivé, ou source secondaire — expliquez la méthode dans `description`.
   - `inconnu` : la donnée n'existe pas publiquement. Ajoutez alors un bloc `inconnu` avec `quoi` (ce qui manque) et `contact` (l'administration à solliciter). C'est une contribution précieuse : cartographier l'ombre fait avancer la transparence.
5. Vérifiez localement : `python3 scripts/build.py --check` (la CI le fera aussi sur votre PR).
6. Ouvrez la pull request en indiquant : source, méthode, et ce que vous n'avez PAS pu vérifier.

## Contributions typiques (par difficulté croissante)

- **Corriger un libellé, enrichir une `description`** — 5 min.
- **Descendre d'un niveau une mission de l'État** (programmes → actions) : lancez `scripts/extract_plf.py` avec le nom de la mission, transformez la sortie au format nœud — ~1 h.
- **Documenter « qui perçoit »** : pour une action donnée, identifier les opérateurs/bénéficiaires via les PAP/RAP (budget.gouv.fr) et le jaune « Opérateurs » — statut `estime` si retraitement.
- **Structurer un tableau PDF** (rapports CCSS, annexe 3 PLFSS) : recopier un tableau en JSON avec la page citée dans `source.nom` — chantier prioritaire.
- **Réclamer une donnée manquante** : déposer une demande sur [madada.fr](https://madada.fr), puis ajouter l'URL de la demande dans le champ `inconnu.url` du nœud. Quand l'administration répond, la donnée entre dans l'arbre.

## Ce qui est refusé

- Chiffres sans source ou avec source cassée (la CI vérifie le format, les mainteneurs vérifient le fond).
- Mélange silencieux de millésimes (chaque nœud porte son `annee`).
- Militantisme dans les `description` : le projet documente les flux, il ne juge pas leur opportunité. La neutralité factuelle est la condition de la confiance.

## Gouvernance

Décisions par consensus dans les issues. Les mainteneurs garantissent la neutralité et la traçabilité, pas une ligne éditoriale.
