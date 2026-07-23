# ADR-0007 — Rendre mécanique la règle du référentiel homogène

- **Statut : Accepté** (2026-07-21, décision du mainteneur)
- **Date : 2026-07-21**
- **Complète** : ADR-0006 §3 et sa note d'application 3

## Contexte

L'ADR-0006 §3 pose la règle anti-triche centrale du projet : **on ne divise jamais un euro d'une comptabilité par un euro d'une autre.** Le coefficient de couverture d'un bloc se mesure dans un référentiel homogène (PLF ÷ PLF, OFGL ÷ OFGL, CCSS ÷ CCSS), puis s'applique au poids SEC.

Cet ADR affirmait aussi : « *Un rapport inter-référentiel est mécaniquement refusé par `build.py`.* »

**C'était faux.** Vérifié ligne à ligne, puis corrigé dans la note d'application 3 :

- `indice_cp()` calculait `c = present / ref["total_eur"]` **sans jamais comparer les bases comptables** des deux termes ;
- `valider_denominateur()` ne contrôlait que la présence d'un `total_eur` non nul et d'une source `https://` ;
- `schema/denominateur.schema.json` ne portait **aucun champ** typant le référentiel.

La seule règle réellement mécanique était `ref is None → c = 0`.

Ce n'est pas une faiblesse théorique. Deux investigations successives l'ont exploitée pour de bon :

| Investigation | Attaque | Gain de C obtenu | CI |
|---|---|---:|---|
| Raccord Sécu (issue #69) | dénominateur DREES branché sur un arbre CCSS | **+30,3 points** | verte |
| Bloc ODAC (issue #71) | référentiel = total du jaune, sur un périmètre couvrant la moitié des unités | **+7,10 points** | verte |

Sur un projet dont la crédibilité est le produit, une règle cardinale tenue par la seule vigilance humaine est un défaut de conception. Il suffit d'une PR de données plausible, relue vite, pour publier un indice faux.

## Décision

**La comptabilité devient une donnée déclarée, et sa cohérence est vérifiée par le build.**

### 1. Une énumération fermée des bases comptables

`build.py` porte `BASES_COMPTABLES` : `PLF`, `OFGL`, `CCSS`, `SEC`.

**Fermée à dessein.** Ajouter une base est une décision qui passe par une relecture de code, jamais un effet de bord d'une PR de données — c'est précisément par un référentiel d'une comptabilité inattendue que la faille s'ouvrait.

### 2. Six règles bloquantes

| | Règle | Ce qu'elle ferme |
|---|---|---|
| **A** | Tout `referentiel_comptage` déclare une `base_comptable` valide | le référentiel muet, sur lequel aucune comparaison n'était possible |
| **B** | Un référentiel en base **`SEC` est refusé** | la circularité : le poids étant déjà en SEC, `c = 1` par construction — le piège du tableau INSEE 3.204 relevé sur les ODAC |
| **C** | Toute racine d'arbre à `bloc_univers` non nul déclare une `base_comptable` valide | l'arbre muet, symétrique du référentiel muet |
| **D** | La base d'un arbre **doit égaler** celle du référentiel de son bloc | **le rapport inter-référentiel lui-même** |
| **E** | Un coefficient **`c > 1`** est refusé | le référentiel au montant fabriqué — voir ci-dessous |
| **F** | Un bloc **compté au-delà de son propre poids** est refusé | filet de dernier recours, indépendant de tout paramétrage |

La règle D est le verrou. A, B et C existent pour qu'il ne puisse pas être contourné par omission. E et F ont été ajoutées **après qu'une revue adversariale du présent ADR eut démontré que D seule ne suffisait pas** (voir « Ce que ce verrou ne fait pas »).

### 3. Où vit l'information

- **Référentiel** : `referentiel_comptage.base_comptable`, champ **requis** (`schema/denominateur.schema.json`).
- **Arbre** : `base_comptable` à la **racine de fichier**, aux côtés de `bloc_univers`, `volet` et `niveaux` (`schema/noeud.schema.json`).
- **Pose** : `qualifier_profondeur.py` — le filet idempotent — et les deux pipelines OFGL, qui l'émettent sur toute fiche nouvelle.

Un bloc **sans** référentiel (`c = 0`) n'est pas concerné par la règle D : il n'y a rien à comparer. Mais son arbre déclare tout de même sa base — ce qui rend le blocage **lisible par machine** au lieu d'être enfoui dans de la prose. `data/secu/*.json` porte désormais `base_comptable: "CCSS"` face à un bloc sans référentiel : la raison du zéro est dans la donnée.

## Ce que ce verrou ne fait PAS

**À énoncer sans détour, sous peine de recréer exactement la surpromesse que cet ADR corrige.**

Le verrou compare des **étiquettes déclarées**. Il ne relit aucune source.

**Une première rédaction de cet ADR s'arrêtait là — et elle surpromettait, exactement comme l'ADR-0006 §3 qu'elle prétendait corriger.** Une revue adversariale l'a établi par exécution, et le compte rendu mérite d'être conservé :

> Diviser par deux le `total_eur` du référentiel de `APUC.etat`, **sans toucher à aucune `base_comptable`** — l'étiquette « PLF » restant parfaitement honnête — produisait un coefficient de **2,0** et faisait passer C de 46,0 % à **76,4 %**, `exit 0`, zéro erreur. Soit les **+30,3 points** de l'attaque historique que ce verrou était censé fermer.

Les règles **E** et **F** répondent à cette attaque : un corpus ne peut dépasser ni son référentiel, ni le poids de son bloc.

**Ce qui reste ouvert, et qu'il faut énoncer sans l'enjoliver :**

1. **Un `total_eur` fabriqué mais plausible passe.** E n'attrape que le débordement au-delà de 1. Sur un bloc dont le coefficient réel est 0,3, rétrécir le référentiel jusqu'à amener `c` à 1,0 reste possible et invisible.
2. **Une étiquette mensongère passe.** `base_comptable: "CCSS"` sur un référentiel issu d'ailleurs satisfait toutes les règles.
3. **Un référentiel entièrement inventé sur un bloc aujourd'hui à zéro passe**, si son montant est choisi égal au corpus présent : `c = 1,0`, aucune règle violée.
4. **Les six règles sont TOUTES intra-bloc : rien ne détecte qu'un même euro soit compté dans DEUX blocs.** Découvert le 21/07/2026 en instruisant les ODASS. L'arbre porte déjà `secu.depenses.maladie.hopital` = 109,4 Md€ (« Établissements de santé (ONDAM) »), en base `CCSS` sous `ASSO.regimes`. Un corpus hospitalier étiqueté `CCSS` et rattaché à `ASSO.odass` réexprimerait ces mêmes euros, satisferait A→F sans une erreur, et gonflerait C d'un montant **faux** — pas seulement nul. Aucune règle actuelle ne le voit.

Ce que le verrou change malgré tout : ces attaques cessent d'être des **omissions** que personne ne remarque pour devenir des **écritures explicites** — une base, un montant — sur des lignes dont c'est l'unique objet, dans un diff. La relecture humaine reste **nécessaire** ; elle sait désormais où regarder.

**Deux contrôles fermeraient le reste** : re-vérifier `total_eur` à sa source, et détecter le recouvrement entre blocs (une même somme d'euros apparaissant sous deux `bloc_univers` distincts). Le premier est, comme `verify-fond.yml` le fait déjà pour les montants de l'arbre. C'est le candidat naturel pour un ADR ultérieur — et il ne faut pas prétendre qu'il est fait tant qu'il ne l'est pas.

> **Mise à jour, 2026-07-23 (ADR-0009).** Le second contrôle — la détection du recouvrement inter-`bloc_univers` — est désormais **fait**, et ferme l'attaque n°4 ci-dessus **à l'agrégat** (copie ou réexpression au montant exact ; une réexpression re-granularisée échappe encore, cf. ADR-0009). Le premier — re-vérifier les `total_eur` des référentiels à leur source — **reste ouvert**.

## Conséquences

- `schema/denominateur.schema.json` : `base_comptable` requise sur `referentiel_comptage` ;
- `schema/noeud.schema.json` : `base_comptable` sur la racine de fichier ;
- `build.py` : `BASES_COMPTABLES`, `BASE_INTERDITE_EN_REFERENTIEL`, `valider_bases_comptables()`, deux contrôles dans `valider_denominateur()` / `valider_racine_cp()`, et les bornes E et F dans `indice_cp()` ;
- `qualifier_profondeur.py` et les deux pipelines OFGL posent le champ ;
- **56 499 fichiers de données** reçoivent une ligne — les 10 référentiels et toutes les racines d'arbres ;
- ADR-0006 §3 : l'avertissement « garde-fou éditorial, non mécanique » est retiré, la phrase d'origine redevenant vraie **dans la limite énoncée ci-dessus**.

**Aucun montant n'est touché. C et P sont strictement inchangés** (46,0269 % / 2,663 et 42,1403 % / 2,000) : ce verrou ne change pas ce que le site mesure, il empêche de le mesurer faux.

## Vérification

Les six attaques rejouées contre le build, chacune refusée avec un message nommant la correction attendue. Les deux dernières ont été trouvées par la revue adversariale de cet ADR, pas par son auteur :

| Attaque | Règle | Verdict |
|---|---|---|
| Référentiel PLF sur l'arbre Sécu (CCSS) | D | `exit 1` |
| Référentiel en base SEC | B | `exit 1` |
| Référentiel d'une base hors énumération | A | `exit 1` |
| Référentiel sans base déclarée — l'attaque historique | A | `exit 1` |
| **`total_eur` ÷ 2, étiquette « PLF » honnête** | **E** | **`exit 1`** |
| **`total_eur` ÷ 100** | **E** | **`exit 1`** |

## Alternatives rejetées

- **Laisser la règle éditoriale et se fier à la revue.** Rejeté : deux investigations ont démontré l'attaque sur ce dépôt même, et un projet public doit résister à un contributeur négligent autant qu'à un contributeur malveillant.
- **Déduire la base du chemin du fichier** (`data/collectivites/**` → OFGL). Rejeté : connaissance implicite logée dans le code, qui dérive dès qu'une source change, et qui n'aurait rien vérifié du côté du référentiel.
- **Énumération ouverte** (`base_comptable` en texte libre). Rejeté : c'est la faille, à peine déplacée — n'importe quelle chaîne devient une base valide.
- **Vérifier que le total vient bien de la source annoncée.** Souhaitable, hors d'atteinte : il faudrait rejouer chaque source à la validation. `verify-fond.yml` fait déjà ce travail sur les montants de l'arbre ; l'étendre aux totaux de référentiels est un candidat pour un ADR ultérieur.
