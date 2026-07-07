# GEMINI.md

Instructions pour Gemini CLI travaillant sur ce dépôt.

**Projet :** « Où va l'argent public ? » — visualisation sourcée des recettes et dépenses publiques françaises. La source de vérité, ce sont les arbres JSON de `data/`.

Ce fichier reprend les mêmes règles que [`AGENTS.md`](AGENTS.md) ; en cas de doute, c'est `AGENTS.md` et `CONTRIBUTING.md` qui font foi.

## Avant toute contribution de données

Lis **`contribuer/ia/kit-de-contribution.md`** (règles + format d'un nœud) et **`schema/noeud.schema.json`** (schéma exact).

## Règles non négociables

- **Tout chiffre a une source officielle** : `source` = { url, producteur, `consulte_le` (AAAA-MM-JJ), `annee` }. Ne jamais inventer ni arrondir en silence. Donnée non publique → nœud `statut: "inconnu"` avec `inconnu.quoi` et `inconnu.contact`.
- **Neutralité** : `description` factuelle, jamais de jugement sur l'opportunité d'un flux.
- Ne jamais mélanger les millésimes ; chaque nœud porte son `annee`.
- Un sujet = une PR. `main` est protégée ; ne jamais committer dessus directement ni auto-merger (revue humaine).

## Boucle de travail

```bash
python3 scripts/build.py --check   # valide data/ (ids, sources, dates, sommes ±2 %)
python3 scripts/build.py           # régénère site/data.js — NE PAS l'éditer à la main
```

Éditer `data/**/*.json` → `build.py --check` vert → branche `data/<sujet>` → PR avec le template.

En cas de doute entre exactitude et exhaustivité : **exactitude, toujours.**
