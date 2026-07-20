# ADR-0006 — Mesurer la complétion contre l'univers réel : l'indice C·P

- **Statut : Accepté** (2026-07-20, décision du mainteneur — fusion de la PR #51)
- **Date : 2026-07-20**

## Contexte

Le site affiche aujourd'hui un baromètre de couverture qui annonce **« 100 % confirmé »** pour les dépenses de l'État. C'est arithmétiquement exact et **trompeur** : cet indicateur mesure la *qualité de source à l'intérieur de ce qui est déjà modélisé*. Il ne dit rien de ce qui manque au **périmètre** (opérateurs, collectivités, volet recettes) ni de ce qui manque en **profondeur** (on voit la ligne budgétaire, jamais qui a touché l'argent).

Or l'ambition du projet est explicitement **bidimensionnelle** : rendre visibles *tous* les euros publics (largeur) *jusqu'à la pièce justificative* (profondeur). Un pourcentage unique ne peut pas exprimer les deux sans en écraser une — et le pourcentage actuel écrase précisément celle qui compte le plus.

Une cartographie du domaine public français a été menée (2026-07-20, 7 axes, chacun soumis à un contradicteur) pour établir le **dénominateur réel** : les comptes des administrations publiques au sens INSEE/SEC 2010.

| | Montant | Source |
|---|---:|---|
| Dépenses des APU 2025 (somme brute des 3 sous-secteurs) | 1 819,9 Md€ | INSEE, *Insee Première* n° 2106 (29/05/2026), comptes **provisoires** |
| Dépenses des APU 2025 (total consolidé publié) | 1 714,2 Md€ | idem |
| Couvert par l'arbre | 611,0 Md€ | calcul du 20/07/2026 |

Soit **33,6 % de périmètre** et une **profondeur de 3,0 / 6** — non 100 %.

## Décision

### 1. Deux nombres, jamais moyennés

L'indice de complétion est le couple **C·P** :

- **C — couverture de périmètre** : part des euros de l'univers APU représentés dans l'arbre par au moins un nœud confirmé ;
- **P — profondeur** : niveau moyen atteint sur l'échelle de destination, **calculé sur les seuls euros couverts**.

Ils sont **toujours affichés ensemble**. Aucun fichier généré ne contient de score global agrégé — un champ `score_global` où que ce soit fait échouer la CI.

### 2. L'échelle de profondeur P0 → P6

C'est une **convention du projet, pas un standard**. Elle est arbitrée ici, une fois, et fermée :

| Niveau | Ce qu'on voit |
|---|---|
| **P0** | agrégat ou sous-secteur non ventilé |
| **P1** | politique publique (mission, branche, strate) |
| **P2** | programme, poste comptable, ou entité administrative nommée |
| **P3** | action et sous-action — la ligne budgétaire fine |
| **P4** | organisme destinataire identifié |
| **P5** | **bénéficiaire final nommé**, avec identifiant machine **et** rattaché à sa ligne payeuse |
| **P6** | **pièce justificative** référencée |

Le rattachement de P5 est ce qui distingue « on sait que cette association a reçu de l'argent » de « on sait **quelle ligne budgétaire** l'a payée ». Sans lui, le niveau reste P4.

### 3. La règle du référentiel homogène (règle anti-triche centrale)

**On ne divise jamais un euro d'une comptabilité par un euro d'une autre.**

Le coefficient de couverture `c` d'un bloc est mesuré **à l'intérieur d'un référentiel homogène** (PLF ÷ PLF, OFGL ÷ OFGL, CCSS ÷ CCSS), puis appliqué au **poids SEC** du bloc. Un rapport inter-référentiel est mécaniquement refusé par `build.py`.

Conséquence assumée et inconfortable : les **666 Md€ de la Sécurité sociale**, pourtant modélisés, sourcés et confirmés, **comptent zéro** tant qu'aucune table de passage CCSS → SEC n'est publiée. Ce n'est pas une donnée manquante, c'est un **raccord** manquant, et la page `/perimetre` doit le dire en clair.

Écrire `666 / 803,3 = 83 %` ferait passer C de 33,6 % à ~70 %. C'est exactement le piège que cet ADR interdit.

### 4. Base brute plutôt que consolidée

C est calculé sur la **somme brute des sous-secteurs (1 819,9 Md€)**, non sur le total consolidé (1 714,2 Md€). Motif : les nœuds de l'arbre sont eux-mêmes bruts (un transfert État → collectivités apparaît dans les deux arbres, chacun le signalant). Utiliser le consolidé au dénominateur avec un numérateur brut gonflerait C. Le total consolidé reste **publié à côté**, comme rappel obligatoire.

### 5. Le plafond légal est un contexte publié, jamais un dénominateur

Ce qui est fermé par le droit (vie privée, secret des affaires, secret de la défense) est documenté dans `data/plafond-legal.json`, avec **fondement juridique cité à l'article**, et affiché sur une page dédiée. **Il n'entre dans aucun quotient.** Sortir ces montants du dénominateur reviendrait à se donner une bonne note en rétrécissant l'épreuve.

Un nœud `inconnu` ne peut porter le bouton « réclamer » que si son bloc n'est pas `ferme-droit` ou `inexistant`.

### 6. Ce que le compteur ne compte pas

Le périmètre S13 **exclut** les entreprises publiques marchandes, les stocks de dette et engagements hors bilan, et les dépenses fiscales. **Un C de 100 % ne réaliserait donc pas l'ambition « tous les euros ».** Cette note est permanente et non repliable, sans quoi un contributeur ajoutera un jour le budget d'une entreprise publique dans l'arbre et le score deviendra faux.

### 7. Libellés non négociables

Vérifiés par `build.py`, qui refuse de générer l'en-tête s'ils manquent :

- « **des euros publics sont dans l'arbre** » — jamais « sont tracés », jamais « sont transparents » ;
- la phrase « **Ce pourcentage mesure le périmètre, pas la finesse** » est solidaire du nombre ;
- « **X % raccordé** » est collé au pourcentage dans le même bloc visuel : le site ne doit jamais pouvoir afficher C seul ;
- l'**histogramme de profondeur n'est pas repliable** — sans la barre P0, un « 3,0 / 6 » se lit « à mi-chemin », ce qui est faux.

### 8. Millésimes versionnés, jamais écrasés

Le fichier de dénominateurs est versionné par millésime (`apu-depenses-2025.json`, puis `2026`). Les comptes INSEE 2025 sont **provisoires** et seront révisés : chaque montant macro porte son statut de révision en plus de l'année.

## Conséquences

- **Nouveau** : `schema/denominateur.schema.json` + `data/denominateurs/apu-depenses-<millésime>.json` (le mapping vit là, `data/` reste intact et l'audit du calcul tient dans un seul fichier) ;
- **Nouveau** : `data/plafond-legal.json` ;
- `schema/noeud.schema.json` : ajout de `bloc_univers` et d'une table `niveaux` à la **racine de fichier**, et d'un `rattachement_id` sur les nœuds bénéficiaires ;
- `build.py` : `charger_denominateurs()`, `profondeur()`, `indice_cp()` → bloc `cp` dans `site/couverture.json` ; **12 règles bloquantes** en CI ;
- le bandeau « % confirmé » **disparaît** ; le baromètre de statuts existant est **conservé mais rétrogradé** et relibellé « Qualité de source — cet indicateur ne dit rien de ce qui manque en périmètre et en profondeur » ;
- trois pages générées : `/perimetre`, `/plafond`, `/methode` ;
- le champ `sens_du_biais` est **obligatoire** sur tout poids dérivé : le contributeur doit déclarer dans quel sens son approximation se trompe.

### Risques acceptés

- **Le contresens par pessimisme.** « 33,6 %, 0 % de bénéficiaires » peut se lire « on ne sait rien de l'argent public ». C'est faux : 100 % du budget de l'État est ventilé jusqu'à la sous-action. La phrase de cadrage est solidaire du nombre, mais aucune parade technique n'empêche une reprise partielle. Risque assumé.
- **P peut être « acheté »** en n'ingérant que des jeux fins et petits. Les deux nombres étant toujours affichés ensemble, l'arbitrage reste visible.
- **Ni C ni P ne mesurent l'exactitude.** Un arbre entièrement faux mais large et profond scorerait bien. C·P mesure la **cartographie**, pas la véracité des montants — d'où le maintien du baromètre de qualité de source à côté.
- **Le site modélise du PLF déposé (prévision) face à un dénominateur d'exécution.** Le drapeau `raccord_publie: false` le signale sans le corriger. C'est le motif le plus solide d'un contradicteur technique.

## Rejeté

- **M1 — couverture de périmètre seule** : aveugle à la profondeur par construction. L'État y compterait 607,7 Md€ que l'arbre s'arrête à la mission ou descende jusqu'au bénéficiaire. Rate la moitié de la promesse du site.
- **M3 — traçabilité bornée par le plafond légal** : 70 % de son dénominateur serait un plafond, c'est-à-dire un **jugement**. Un dénominateur discrétionnaire est le contraire de la règle d'or. Sa manchette à 0,7 % invitait au contresens « on ne sait rien ».
- **Un pourcentage unique agrégé** : quelle que soit la pondération, il permet de compenser une profondeur nulle par un périmètre large. C'est le trompe-l'œil actuel sous une autre forme.
- **Assouplir la règle du référentiel homogène** pour que la Sécu compte : gain immédiat de 36 points de C, au prix d'un ratio entre deux comptabilités incomparables. Refusé mécaniquement, et c'est le motif principal de l'existence de cet ADR.

---

## Note d'application — 2026-07-20 : précision sur le raccord CCSS → SEC

L'ADR écrit plus haut, au §3, que les 666 Md€ de la Sécurité sociale comptent zéro **« tant qu'aucune table de passage CCSS → SEC n'est publiée »**. Cette formulation est **imprécise et doit être lue à la lumière de la présente note** : une investigation dédiée (quatre pistes — INSEE, DREES, DSS/PLFSS, composantes à retrancher — chacune soumise à réfutation) a établi que **de telles tables existent bel et bien**.

Vérification en première main du tableau INSEE **3.108** « Passage du résultat comptable du régime général au déficit des administrations de sécurité sociale (S1314) au sens de Maastricht » (fichier `t_3108_fr.xlsx`, comptes nationaux base 2020, millésime 2025). Sa notice énonce qu'il « permet de réconcilier le résultat comptable du régime général de la sécurité sociale calculé par la Commission des Comptes de la Sécurité Sociale et le déficit au sens de Maastricht des administrations de sécurité sociale calculé par l'Insee ».

**La décision du §3 est néanmoins confirmée, et sans réserve** : cette table ne raccorde pas ce que le site modélise, pour trois raisons cumulatives.

1. **Elle convertit un solde, jamais des dépenses.** Elle part d'un résultat comptable (−20,8 Md€ en 2025) et arrive à une capacité/besoin de financement (−20,3 Md€ pour le régime général, −6,7 Md€ pour l'ensemble des ASSO). Aucune ligne de dépenses. Convertir 666 Md€ de dépenses est une impossibilité **de nature**, pas une lacune de granularité.
2. **Son périmètre de départ n'est pas celui du site** : « régime général » (CNAF, CNAM, CNAV, FSV — la notice y ajoute la CNSA depuis 2021 sans que le libellé de ligne l'ait suivi), strictement plus étroit que « régimes de base + FSV ».
3. **Elle arrive à S1314**, l'ensemble des ASSO, et non à S13141.

**Ce que cette note change** : la formule « aucune table de passage n'est publiée » ne doit plus être employée, ni dans le dépôt, ni sur le site. La formulation exacte est : *aucune ventilation en dépenses de S13141 n'est publiée, et les tables de passage existantes portent sur le solde et sur un périmètre plus étroit.*

**Pourquoi cette correction compte** : une affirmation d'absence fausse est précisément ce qui ferait tomber la crédibilité du site au premier contradicteur informé. Le projet préfère corriger une de ses propres phrases plutôt que de la défendre.

Le champ `manque` du sous-segment `ASSO.regimes` porte désormais l'énoncé exact de ce qui manque et le contact à saisir (INSEE — Département des comptes nationaux).

---

## Note d'application — 2026-07-20 (2) : le raccord LOLF → SEC, et une règle de rédaction

Investigation de l'étape 12 de l'issue #50. Elle porte sur le sous-segment `APUC.etat`, qui représente à lui seul **77 % du numérateur de C** : c'est le point où la crédibilité de l'indice se joue.

### Ce qui a été établi

Le fichier de dénominateurs affirmait qu'**« aucune table de passage LOLF→SEC n'est publiée »**. **C'est faux.** Vérification en première main du tableau INSEE **3.107** « Passage du résultat d'exécution des lois de finances au déficit de l'État (S13111) au sens de Maastricht » : sa notice énonce qu'il « permet de réconcilier deux chiffres clés des finances de l'État : le Résultat d'exécution des lois de finances d'une part et le Déficit de l'État au sens de Maastricht d'autre part ».

**La décision reste néanmoins inchangée** — `raccord_publie: false` — pour deux raisons cumulatives :

1. **Elle convertit un solde, jamais des dépenses.** Elle part de −124,7 Md€ de résultat d'exécution 2025 et arrive à un déficit. Aucune ligne de dépenses. Convertir 823 Md€ de crédits de paiement est une impossibilité **de nature**.
2. **Son point de départ n'est pas le nôtre** : l'**exécution constatée**, quand l'arbre modélise le **PLF déposé** (prévision).

Ce qui manque est donc précis : une réconciliation **en dépenses** entre les crédits de paiement LOLF (823,04 Md€) et les dépenses de l'État en comptabilité nationale (607,70 Md€, tableau 3.203) — un écart de **215,34 Md€**, dont 147,14 Md€ de remboursements et dégrèvements neutralisés en SEC. Le reconstituer soi-même serait un travail original, que la règle d'or interdit.

### La règle de rédaction que cette note ajoute

**C'est la deuxième fois que le projet affirme à tort qu'une table de passage n'existe pas** — après le raccord CCSS → SEC (note d'application 1, tableau 3.108). Les deux fois, une table officielle existait et ne faisait simplement pas ce dont le projet avait besoin.

Le motif est identique et prévisible : on constate qu'un raccord est *inutilisable*, et on l'écrit *inexistant*. Sur un projet dont la crédibilité est le produit, une affirmation d'absence fausse est ce qui tombe en premier face à un contradicteur informé.

**Règle : le dépôt n'écrit jamais qu'une donnée « n'existe pas ».** Il écrit ce qui a été cherché, où, et ce qui a été trouvé — puis pourquoi cela ne convient pas. Toute affirmation d'absence porte le périmètre de la recherche qui la fonde, et reste réfutable.

Les champs `manque.quoi` des sous-segments `APUC.etat` et `ASSO.regimes` sont rédigés selon cette règle.
