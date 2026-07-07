# ADR-0003 — L'axe temps : millésimes successifs et voté vs exécuté

- **Statut : Proposé** (décision à prendre dans la PR — commentaires bienvenus)
- **Date : 2026-07-07**

## Contexte

Deux réalités temporelles que le modèle actuel ne distingue pas :

1. **Les millésimes se succèdent.** L'arbre actuel est de fait mono-millésime (PLF 2025). Que se passe-t-il à l'arrivée du PLF 2026 ? Écraser ferait perdre l'historique ; ne rien décider produira un mélange silencieux — exactement ce que la règle d'or interdit.
2. **Voté ≠ exécuté.** Le PLF est une *intention* ; « chaque euro dépensé » désigne l'*exécution* (données d'exécution, lois de règlement). Les deux sont légitimes et **doivent coexister sans se confondre** : l'écart voté/exécuté est lui-même une information précieuse. C'est aussi la première critique qu'un connaisseur fera au site (« vous montrez un projet de loi, pas des dépenses »).

## Options

**A. Photo courante** — on écrase à chaque millésime.
- ✅ simple ; ❌ perte d'historique, pas de comparaison, mélange voté/exécuté irrésolu.

**B. Un arbre par exercice** *(recommandée pour commencer)*
- `data/etat/2025/…`, `data/etat/2026/…` : chaque exercice est un arbre complet, le site s'ouvre sur le plus récent avec un sélecteur d'année.
- ✅ simple à comprendre et à contribuer, isolation naturelle des millésimes, l'historique est dans les fichiers (pas seulement dans git) ; ❌ duplication de structure entre années (acceptable : la structure budgétaire change réellement d'une année à l'autre), comparaison inter-années à construire côté site.

**C. Nœuds multi-valeurs** — chaque nœud porte `montants: [{annee, phase, valeur, source}]`.
- ✅ comparaison native, pas de duplication ; ❌ complexifie le schéma et chaque contribution (le format simple actuel est un atout), migration lourde, mélange plus facile à rater en revue.

## Décision proposée

**Option B maintenant, C réévaluée plus tard** si la comparaison inter-années devient centrale. Plus, dès maintenant et quel que soit le choix :

- ajouter au schéma un champ **`phase`** optionnel : `"vote"` (défaut, ne change rien à l'existant) ou `"execute"` — pour pouvoir accueillir les données d'exécution **sans** les confondre avec le voté ;
- règle d'affichage : le site distingue toujours visuellement voté et exécuté (jamais additionnés, jamais côte à côte sans étiquette) ;
- règle de contribution : une PR ne mélange pas deux exercices (déjà l'esprit de « une PR = un sujet »).

## Non-décidé volontairement

- La stratégie de comparaison inter-années (vue diff, évolutions) — attendra la lentille UX (#18) ;
- le traitement des exercices communaux (N+1 exécuté) — chaque nœud portant déjà son `annee`, l'option B s'applique par périmètre, pas besoin d'un calendrier unifié.

## Conséquences

- Schéma : champ `phase` optionnel (rétro-compatible, défaut `vote`) ;
- restructuration en dossiers par exercice à faire **en même temps** que le découpage de l'ADR-0002 (une seule migration) ;
- documentation : README (« vous regardez le PLF 2025 — voté ») + CONTRIBUTING ;
- ouvre la porte au chantier « exécution » (nouvelle source, nouvelle branche de backlog).
