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

Le coefficient de couverture `c` d'un bloc est mesuré **à l'intérieur d'un référentiel homogène** (PLF ÷ PLF, OFGL ÷ OFGL, CCSS ÷ CCSS), puis appliqué au **poids SEC** du bloc.

**Cette règle est désormais mécanique — voir l'ADR-0007** (21/07/2026), qui l'implémente après que la note d'application 3 eut établi que la présente section promettait un verrou inexistant. Le référentiel et l'arbre déclarent chacun leur `base_comptable` ; `build.py` refuse un référentiel muet, un référentiel en base SEC (circulaire), un arbre muet, et surtout **toute divergence entre la base de l'arbre et celle du référentiel de son bloc**.

⚠️ **Limite à connaître, et à ne pas surpromettre une seconde fois** : le verrou compare des **étiquettes déclarées**, il ne relit pas les sources. Un référentiel étiqueté `CCSS` mais réellement issu d'une autre comptabilité passerait. Ce qui change, c'est que l'erreur cesse d'être une omission invisible pour devenir une ligne explicite dans le diff. La relecture humaine reste requise — elle sait maintenant où regarder.

Conséquence assumée et inconfortable : les **666 Md€ de la Sécurité sociale**, pourtant modélisés, sourcés et confirmés, **comptent zéro**. Ce n'est pas une donnée manquante, c'est un **raccord** manquant, et la page `/perimetre` doit le dire en clair. La note d'application 3 établit que ce raccord est impossible pour une raison plus profonde qu'une lacune de publication : les deux périmètres ne s'emboîtent pas.

Écrire `666 / 682,5 = 97,6 %` ferait passer C de 46,0 % à ~83,5 %. C'est exactement le piège que cet ADR interdit — et ce quotient est en outre substantiellement absurde, S13141 contenant l'AGIRC-ARRCO et l'UNEDIC que l'arbre ne modélise pas.

**Corollaire non évident, à ne pas redécouvrir à ses dépens : un bloc à `c = 0` est absent de P autant que de C.** `comptes = c × poids_eur` ; avec `c = 0`, aucun euro du bloc n'entre dans l'histogramme de profondeur. Approfondir la Sécu jusqu'à P6 laisse P strictement inchangé (vérifié : 2,663 avant et après). Ce comportement est **voulu** — sans lui, la faille que la règle ferme sur C se rouvrirait par P — mais il signifie qu'aucun travail d'approfondissement sur un bloc non raccordé ne fait bouger l'indice.

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

## Note d'application — 2026-07-20 (3) : le raccord Sécu est impossible, et la question était mal posée

Investigation dédiée : sept pistes instruites en parallèle sur sources primaires (couverture intégrale de S13141 · INSEE au-delà de 3.108/3.212 · DSS-PLFSS-CCSS · DREES · soustraction des composantes · doctrine · axe P), chacune ensuite soumise à deux réfutations adversariales indépendantes (règle anti-triche · coïncidence des périmètres). **Sept pistes, sept réfutées.** Cette note enregistre ce que l'investigation a établi, y compris contre le dépôt lui-même.

### 1. Le blocage n'est pas documentaire, il est de nomenclature

Le dépôt réclamait à l'INSEE « une ventilation en dépenses de S13141 isolant les régimes obligatoires de base + FSV ». **Cet objet ne peut pas exister** : « régimes de base + FSV » n'est pas un sous-ensemble de S13141. Les deux périmètres se croisent sans qu'aucun ne contienne l'autre.

Le régime des fonctionnaires civils et militaires de l'État (~65 Md€) et le FSPOEIE (~2 Md€) sont **dans** les 666,0 Md€ du CCSS mais enregistrés en **S13111 (État)** en comptabilité nationale : servis sans caisse, ce sont des services de l'État.

Preuve arithmétique, indépendante de toute affirmation de classement : S13141 brut = 766,3 Md€. Si les 666,0 Md€ y étaient inclus, il ne resterait que 100,3 Md€ pour l'AGIRC-ARRCO (~100 Md€ à elle seule), l'UNEDIC (45,0), la CADES et le FRR. **Déficit de contenance ≥ 45 Md€.**

**Conséquence : même publiée demain, la ventilation réclamée ne raccorderait rien.**

**Corollaire à ne pas manquer** : ces euros de pensions FPE sont **déjà comptés** dans le numérateur de C, via `APUC.etat` (référentiel PLF, `c = 1,000`). Un raccord naïf de la Sécu aurait donc **double-compté ~67 Md€** — et un « minorant prudent » déclaré `sens_du_biais: sous-estime` aurait été faux dans son sens même.

### 2. Formulation correcte, à employer désormais

> Aucune ventilation en dépenses de S13141 par organisme ou par régime n'est publiée ; **et** le périmètre CCSS « régimes de base + FSV » n'est de toute façon pas inclus dans S13141 — les régimes servis sans caisse par l'État en sont exclus, tandis que S13141 inclut des organismes que l'arbre ne modélise pas.

Ce qui débloquerait la situation est une publication unique satisfaisant **les trois conditions à la fois** : porter sur des **dépenses** (pas un solde) ; être en **concepts SEC**, produite par l'INSEE ou sous son calage ; et isoler à l'intérieur de S13141 un périmètre d'unités explicitement défini **tout en publiant symétriquement** le montant SEC des régimes de base logés hors S13141.

### 3. Correction d'une surpromesse de cet ADR

Le §3 affirmait : « *Un rapport inter-référentiel est mécaniquement refusé par `build.py`.* » **C'est faux**, et le §3 est corrigé en conséquence.

Vérifié ligne à ligne : `indice_cp()` calcule `c = present / ref["total_eur"]` sans jamais comparer les bases comptables ; `valider_denominateur()` ne contrôle que la présence d'un `total_eur` non nul et d'une source `https://` ; `schema/denominateur.schema.json` ne porte aucun champ typant le référentiel. La seule règle réellement mécanique est `ref is None → c = 0`.

Démonstration par exécution obtenue pendant l'investigation : on peut renseigner un dénominateur DREES face à un arbre CCSS, gagner **+30,3 points de C, et passer la CI en silence**.

**La règle anti-triche est tenue par la convention et la relecture humaine, pas par le code.** Rendre la phrase vraie supposerait un champ `base_comptable` sur le référentiel *et* sur les racines d'arbres, comparé à la validation. Cette option est **identifiée, non retenue à ce stade** — elle modifie le schéma et la doctrine, et relève d'un ADR propre.

### 4. Ce qui a été cherché, et où

Sources primaires ouvertes : INSEE `t_3108_fr.xlsx` (passage du solde, périmètre régime général, arrivée S1314) et `t_3213_fr.xlsx` (compte de S13141 — total du sous-secteur, jamais sa partition) ; Eurostat `gov_10a_main` (granularité S1314 maximum) ; annexe 5 du PLFSS 2026 et tableau 23 du RESF (isole régime général + FSV, pas ROBSS + FSV, et n'est pas une partition exhaustive) ; annexe 1 méthodologique des Comptes de la protection sociale édition 2025 et jeu open data DREES n° 305 (`si_code = S13141` — troisième référentiel, champ Sespros, hors Mayotte, prestations incluant des crédits d'impôt ; CPS 2024 = 823,6 Md€ contre INSEE 3.213 = 740,5 Md€ sur millésime identique) ; catalogues open data AMELI, ATIH/ScanSanté, CNAF/Cafdata.

Bornes de cette recherche, à énoncer avec elle : les fichiers CSV des catalogues de santé n'ont pas été téléchargés et inspectés colonne par colonne — les conclusions de granularité reposent sur les pages de description des producteurs. Les 52+ jeux « professionnels de santé libéraux » du catalogue AMELI n'ont pas été parcourus un par un. Cet angle reste formellement ouvert, mais il ne peut pas changer le verdict : le gain d'indice serait nul quelle que soit la granularité trouvée, un bloc à `c = 0` étant absent de P comme de C.

## Note d'application — 2026-07-21 : l'axe P a son plafond, et il avait sa faille

Investigation dédiée sur l'axe P de l'État : 4 gisements instruits, chacun soumis à 2 réfutations, tous les gains **mesurés par ré-exécution d'`indice_cp()`**, jamais estimés.

### 1. Le taux de change, à connaître avant toute promesse

> **1 Md€ de crédits reclassé de P3 vers P5 vaut +0,00160 point de P.**

Il vient de la mécanique : pour `APUC.etat`, `comptes = c × poids_eur` donne une échelle de 551,90 / 823,04 = **0,6706** — un euro de l'arbre État ne pèse que 0,67 euro d'univers — multipliée par 2 crans, divisée par les 837,62 Md€ couverts. **Faire bouger P d'un dixième de point exige de reclasser ~42 Md€.**

### 2. Le gain réellement disponible : +0,023

| Gisement | Euros traçables | ΔP |
|---|---:|---:|
| Associations, plafond `[:5]` retiré | 10,655 Md€ | +0,013 |
| Opérateurs mono-programme | 6,534 Md€ | +0,011 |
| Opérateurs multi-programmes | 47,764 Md€ | **0** — non ventilable |
| Commande publique (DECP) | 72,4 Md€ | **0** — aucun lien vers la ligne budgétaire |

**P est proche de son plafond structurel, pour la même raison que C : ce sont les sources qui manquent.** Les DECP ne portent aucun rattachement budgétaire (schéma officiel v2.0.3 inspecté : ni `programme`, ni `imputation`, ni `chorus`). Le jaune des opérateurs agrège 85,6 % de ses montants sur plusieurs programmes.

### 3. La faille : P était achetable, et personne ne le voyait

L'ADR-0007 a rendu mécanique la règle qui protège **C**. **Rien ne protégeait P.** Vérifié par exécution : pointer 100 Md€ de bénéficiaires sur `etat.depenses.BG.VA.177`, un programme qui porte 2,93 Md€, faisait passer P de 2,663 à **2,823** — `exit 0`, zéro erreur. Le plafond de `collecter_p5()` ne s'y opposait pas : il porte sur le **bloc entier** (823 Md€), consommé à moins de 1 %.

`valider_sur_rattachement()` ferme cette porte : une ligne payeuse ne peut pas verser plus qu'elle ne porte. Au-delà de **×3**, erreur fatale ; entre ×1 et ×3, avertissement — parce qu'un écart de millésime est légitime et se produit réellement (le programme 350, « JO 2024 », reçoit 69,5 M€ de versements d'exécution 2023 pour 48,2 M€ de crédits au PLF 2025, soit ×1,44).

### 4. Le piège à ne pas « découvrir » comme une optimisation

**Poser `niveaux[6] = "P4"` sur `data/etat/depenses.json` ferait passer P de 2,663 à 2,864 — +0,201 pour un caractère. Ce serait FAUX.** La profondeur 6 de l'arbre État porte les **titres LOLF** (personnel, fonctionnement, intervention) : une **nature** de dépense, jamais un « organisme destinataire ». Le `null` actuel est correct et doit le rester.

C'est le plus gros gain unitaire du dépôt, il coûte une édition d'un caractère, et **aucune règle de `build.py` ne s'y oppose**. Il est consigné ici pour que sa découverte soit une lecture, pas une tentation.

### 5. P4 est fermé par l'architecture, pas par les données

`niveaux` est indexée par la **profondeur JSON**, et l'arbre de l'État n'est pas de profondeur uniforme : 569,13 Md€ se posent à la profondeur 5, 253,92 Md€ à la profondeur 6. Aucun cran sémantique « organisme destinataire » ne peut donc être déclaré à une profondeur unique — ajouter un 8ᵉ cran rapporte exactement 0 (vérifié). Par ailleurs `collecter_p5()` n'a pas d'équivalent P4 : un nœud portant un `identifiant` mais aucun `rattachement_id` ne rapporte rien.

**Toute profondeur gagnée sur l'État passe donc obligatoirement par la vue transverse et le mécanisme P5.** Ouvrir P4 supposerait soit de normaliser la profondeur de l'arbre, soit de faire porter à chaque nœud son cran sémantique — un ADR, pas une PR de données.

### 6. Rappel vérifié

Tout rattachement visant un nœud d'un bloc à `c = 0` (Sécu, ODAC, ODASS, ODAL) vaut **strictement zéro** — 40 Md€ pointés sur `secu.depenses` laissent P inchangé. Un futur pipeline de rattachements doit refuser ces cibles, ou au minimum les signaler.
