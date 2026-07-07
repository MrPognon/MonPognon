# CLAUDE.md — Où va l'argent public ?

Site open source de visualisation des flux d'argent public français (État, Sécurité sociale, collectivités), depuis la fiche de paie jusqu'à l'action budgétaire la plus fine. L'incomplétude est assumée et VISIBLE : chaque nœud porte un statut (`confirme` / `estime` / `inconnu`) et les données manquantes affichent qui contacter pour les obtenir.

## Règle d'or (non négociable)

**Tout chiffre a une source officielle : URL + producteur + date de consultation + millésime (`annee`) + date de maj du jeu source (`source.maj`).** Ne JAMAIS inventer ou arrondir un chiffre "de tête". Ne jamais mélanger silencieusement des millésimes. Statut `confirme` = extrait tel quel de la source ; tout calcul dérivé = `estime` avec méthode expliquée dans `description`.

## Architecture

- `data/**/*.json` — source de vérité. Un arbre par fichier, nœuds conformes à `schema/noeud.schema.json`.
- `scripts/build.py` — valide data/ (ids uniques, sources, cohérence des sommes ±2 %) et génère `site/data.js`. **À relancer après toute modif de data/. `site/data.js` est généré, ne jamais l'éditer à la main.**
- `scripts/extract_plf.py` — modèle d'extraction API data.economie.
- `site/index.html` — site statique (D3 depuis cdnjs, zéro build front). Trois modes : Dépenses / Recettes / Ma fiche de paie.
- `data-sources/raw/` — extraits bruts des API (traçabilité des transformations).
- `.github/workflows/validate.yml` — CI : `python3 scripts/build.py --check` sur chaque PR.

## Commandes

```bash
python3 scripts/build.py --check   # validation seule (ce que fait la CI)
python3 scripts/build.py           # validation + régénération de site/data.js
python3 -m http.server -d site     # prévisualiser http://localhost:8000
```

## État des données (07/2026)

- **État / dépenses** : COMPLET au niveau open data — PLF 2025 intégral (BG 594,04 Md€ + CAS + CCF + BA = 823 Md€), missions → programmes → actions → sous-actions, 1 203 nœuds, tout `confirme`.
- **État / recettes** : COMPLET — les 156 lignes de l'état A (588,4 Md€), tout `confirme`.
- **Sécu et collectivités** : ordres de grandeur `estime` à remplacer par des extractions sourcées (voir backlog).
- 1 394 nœuds au total ; `site/data.js` ≈ 1 Mo.

## Pièges techniques connus

- API data.economie (ODS Explore v2.1) : parenthèses et quotes des query params DOIVENT être URL-encodées (`sum%28cp%29`), sinon 400. Pour les gros volumes, utiliser `/exports/json` avec `curl --compressed` (le serveur renvoie du gzip).
- API OFGL (`ofgl-base-communes`…) : `exer` est un champ **date** — filtrer avec `year(exer)=2024`, jamais `exer="2024"` (erreur `IncompatibleTypesInComparisonFilter`). Découvert en test terrain 07/2026.
- Dates de maj des jeux : `metas.default.modified` sur l'endpoint dataset de l'API ODS.
- Rupture M14→M57 (2024) dans les balances communales ; fusions de communes → toujours passer par le COG INSEE millésimé.
- Le circuit recette→branche Sécu n'est PAS bijectif (TVA affectée ~28 %, taxe sur les salaires, compensations) : ne jamais forcer une correspondance 1:1.

## Git / PR

- Branches : `data/<sujet>`, `site/<sujet>`, `docs/<sujet>`. Commits en français, impératif, préfixés (`data:`, `site:`, `ci:`, `docs:`).
- Une PR = un sujet. Corps de PR : source(s) utilisée(s), méthode, ce qui n'a PAS pu être vérifié. La CI doit passer.
- Ne jamais commiter de secrets ; le repo est public.

## Contraintes juridiques

- Données : Licence Ouverte 2.0 — mention de source obligatoire (faite nœud par nœud).
- Code du projet : **AGPL-3.0**.
- **DSFR interdit** : le Système de Design de l'État (composants, bleu France #000091, police Marianne, bloc République) est réservé aux sites de l'État. Le site utilise un thème "inspiré" documenté dans le README — ne pas s'en rapprocher davantage.
- Neutralité : les `description` documentent les flux, jamais d'opinion sur leur opportunité.

## Backlog priorisé

1. Ventiler les actions État par nature (champs `titre`/`categorie` du même jeu source — extraction directe).
2. Structurer les comptes Sécu : tableaux CCSS + annexe 3 PLFSS (PDF → JSON, citer la page dans `source.nom`).
3. Sélecteur de commune branché sur l'API OFGL (fiche réelle par commune) — commencer par un appel côté client sur `ofgl-base-communes` avec code INSEE.
4. « Qui perçoit » : jaune Opérateurs (liste 2026 en data) + subventions associations (jeu data.economie).
5. Recettes : enrichir chaque ligne d'impôt avec « qui paie » (IRCOM pour l'IR, stats DGFiP).
6. Réclamations publiques des nœuds ❓ via madada.fr ; tracer l'URL de la demande dans `inconnu.url`.
7. Perf : si data.js > ~3 Mo, découper le chargement par branche (fetch à l'expansion).

## Référence documentaire

`docs/etude-donnees.md` — étude complète des sources (inventaire, granularité, licences, 13 inconnues documentées avec contacts, APIs). La lire avant tout travail sur les données.
