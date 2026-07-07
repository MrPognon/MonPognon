# AGENTS.md

Instructions pour tout assistant de code (Codex, Cursor, agents génériques) travaillant sur ce dépôt.

**Projet :** « Où va l'argent public ? » — visualisation sourcée des recettes et dépenses publiques françaises. La source de vérité, ce sont les arbres JSON de `data/`.

## Avant toute contribution de données

Lis **`contribuer/ia/kit-de-contribution.md`** (règles + format d'un nœud) et **`schema/noeud.schema.json`** (schéma exact). Le guide humain complet est dans `CONTRIBUTING.md`.

## Règles non négociables

- **Tout chiffre a une source officielle** : `source` = { url, producteur, `consulte_le` (AAAA-MM-JJ), `annee` }. Ne jamais inventer ni arrondir en silence. Donnée non publique → nœud `statut: "inconnu"` avec `inconnu.quoi` et `inconnu.contact`.
- **Neutralité** : `description` factuelle, jamais de jugement sur l'opportunité d'un flux.
- Ne jamais mélanger les millésimes ; chaque nœud porte son `annee`.
- Un sujet = une PR. Ne jamais committer directement sur `main` (protégée). Ne jamais auto-merger (revue humaine).

## Boucle de travail

```bash
python3 scripts/build.py --check   # valide data/ (ids, sources, dates, sommes ±2 %)
python3 scripts/build.py           # régénère site/data.js — NE PAS l'éditer à la main
```

Éditer `data/**/*.json` → `build.py --check` vert → branche `data/<sujet>` → PR avec le template (source, méthode, ce qui n'a pas pu être vérifié).

## Pièges

- API ODS data.economie : URL-encoder `(` `)` et quotes des query params (`sum%28cp%29`), sinon 400 silencieux.
- Circuit recette → branche Sécu non bijectif : passer par un nœud « transferts » explicite.
- Collectivités : rupture M14 → M57 (2024) ; passer par le COG INSEE millésimé.

En cas de doute entre exactitude et exhaustivité : **exactitude, toujours.**
