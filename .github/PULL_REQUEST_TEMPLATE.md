<!--
Une PR = un sujet. Merci de remplir chaque section : la traçabilité des sources
est une obligation (Licence Ouverte 2.0), pas une formalité.
-->

## Sujet

<!-- En une phrase : que change cette PR ? -->

## Source(s)

<!--
Pour chaque chiffre ajouté ou modifié :
- URL de la source officielle (jeu de données, page, PDF avec n° de page)
- Producteur (DGFiP, DREES, CCSS, Insee, OFGL…)
- Date de consultation
- Millésime des données (`annee`)
- Date de mise à jour du jeu source (`source.maj`)
-->

-

## Méthode

<!--
Comment les chiffres ont-ils été obtenus/transformés ? (extraction API, lecture PDF,
calcul dérivé…). Un calcul dérivé ⇒ statut `estime` avec la méthode dans `description`.
-->

## Ce que je n'ai PAS pu vérifier

<!--
Trous, approximations, écarts de sommes, millésimes hétérogènes, correspondances
non bijectives (ex. recette → branche Sécu). Un trou assumé = un nœud `inconnu`
avec le contact, jamais une estimation non sourcée.
-->

## Checklist

- [ ] `python3 scripts/build.py --check` passe en local (`OK — … nœuds validés`)
- [ ] `site/data.js` régénéré via `python3 scripts/build.py` si `data/` a changé (jamais édité à la main)
- [ ] Chaque nouveau nœud a un statut (`confirme` / `estime` / `inconnu`) et une `source` complète
- [ ] Aucun secret, token ou donnée personnelle dans le diff
- [ ] Neutralité respectée : les `description` documentent le flux, sans juger son opportunité
