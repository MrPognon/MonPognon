---
name: contribuer-donnee
description: Aide un contributeur à ajouter ou préciser une donnée de finances publiques dans ce dépôt, de la source jusqu'à la pull request. Utilise quand l'utilisateur dit "aide-moi à contribuer une donnée", "j'ai trouvé un chiffre", "ajoute cette dépense/recette", ou fournit une source (data.gouv, PDF, budget de commune…).
---

# Contribuer une donnée — pas à pas

Tu aides une personne (souvent non technique) à transformer une **information officielle** en contribution valide au projet « Où va l'argent public ? ».

## Contexte à charger d'abord

Lis, dans l'ordre :
1. `contribuer/ia/kit-de-contribution.md` — les règles, le format d'un nœud, les statuts.
2. `schema/noeud.schema.json` — le schéma exact.
3. Le fichier `data/` concerné (selon le préfixe d'id : `etat.depenses.` → `data/etat/depenses.json`, etc.) pour trouver le bon parent et t'aligner sur le style existant.

## Règles non négociables

- **Aucun chiffre sans source officielle** (URL + producteur + `consulte_le` + `annee`). Ne jamais inventer ni arrondir en silence. Si la donnée n'est pas publique → nœud `statut: "inconnu"` avec `inconnu.quoi` et `inconnu.contact`.
- **Neutralité** : `description` factuelle, jamais de jugement.
- **Un sujet = une PR.**

## Déroulé

1. **Recueillir** : demander à l'utilisateur la source (lien), le(s) chiffre(s), l'année, l'intitulé exact, et où ça se range (proposer si l'utilisateur ne sait pas).
2. **Construire** le(s) nœud(s) JSON conformes au schéma. Choisir le `statut` juste (`confirme` = copié tel quel ; `estime` = calcul, méthode dans `description` ; `inconnu` = non public).
3. **Insérer** dans le tableau `enfants` du parent logique, dans le bon fichier `data/`.
4. **Valider** : `python3 scripts/build.py --check` doit rester vert (ids uniques, sources, dates `AAAA-MM-JJ`, sommes ± 2 %). Corriger si besoin. Ne PAS éditer `site/data.js` à la main (généré).
5. **Proposer la PR** :
   - Si `gh` est disponible et authentifié : créer une branche `data/<sujet>`, committer (message en français, préfixe `data:`), pousser, ouvrir la PR avec le template (source, méthode, ce qui n'a pas pu être vérifié). **Ne jamais auto-merger** — revue humaine.
   - Sinon : guider l'utilisateur pour le faire dans le navigateur (fichier sur GitHub → ✏️ Edit → coller → « Propose changes »).

## Rappels

- Millésimes : chaque nœud porte son `annee`, jamais de mélange.
- Circuit recette → branche Sécu non bijectif : passer par un nœud « transferts » explicite.
- En cas de doute entre exactitude et exhaustivité : **exactitude**, toujours. Un nœud `inconnu` bien documenté vaut mieux qu'une estimation non sourcée.
