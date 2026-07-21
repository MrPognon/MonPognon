# CLAUDE.md — Où va l'argent public ?

Site open source de visualisation des flux d'argent public français (État, Sécurité sociale, collectivités), depuis la fiche de paie jusqu'à l'action budgétaire la plus fine. L'incomplétude est assumée et VISIBLE : chaque nœud porte un statut (`confirme` / `estime` / `inconnu`), les données manquantes affichent qui contacter pour les obtenir, et un compteur de complétion mesure en permanence ce qui manque encore.

## Règle d'or (non négociable)

**Tout chiffre a une source officielle : URL + producteur + date de consultation + millésime (`annee`) + date de maj du jeu source (`source.maj`).** Ne JAMAIS inventer ou arrondir un chiffre "de tête". Ne jamais mélanger silencieusement des millésimes. Statut `confirme` = extrait tel quel de la source ; tout calcul dérivé = `estime` avec méthode expliquée dans `description`.

**Corollaire, appris à nos dépens (ADR-0006, note d'application 2) : ne jamais écrire qu'une donnée « n'existe pas ».** Écrire ce qui a été cherché, où, ce qui a été trouvé, et pourquoi cela ne convient pas. Toute affirmation d'absence porte le périmètre de la recherche qui la fonde. Le dépôt a affirmé deux fois à tort qu'une table de passage n'existait pas : elle existait, et ne faisait simplement pas l'affaire.

## Architecture

- `data/**/*.json` — source de vérité. Un arbre par fichier, nœuds conformes à `schema/noeud.schema.json`. Chaque racine de fichier déclare `bloc_univers`, `volet`, `base_comptable` (ADR-0007) et une table `niveaux` (ADR-0006). ⚠️ **Les `schema/*.json` sont documentaires : aucun script ne les charge.** `build.py` valide à la main (`validate`, `valider_flux`, `valider_denominateur`, `valider_racine_cp`) — toucher au validateur sans toucher au schéma les fait diverger en silence.
- `data/collectivites/<échelon>/…` — **fiches de collectivités** (ADR-0004), 7 échelons : `communes/<dept>/<insee>.json`, `groupements`, `departements`, `regions`, `syndicats`, `ccas`, `sdis`. Racine à `montant: null` + enfants `.depenses`/`.recettes` (les deux ne s'additionnent pas). Publiées en **fragments** `site/data/<échelon>/<code>.json` chargés à la demande — **jamais dans `data.js`**, jamais sommées dans l'arbre national.
- `data/flux/flux.json` — **flux entre administrations** (ADR-0001) : pôles + flux typés, champs obligatoires `{id, de, vers, label, montant, annee, statut, source}` (+ `noeuds_lies` facultatif), schéma `schema/flux.schema.json`.
- `data/denominateurs/apu-{depenses,recettes}-2025.json` — **l'univers des administrations publiques** contre lequel se mesure la couverture (ADR-0006), poids lus dans les comptes nationaux INSEE. Schéma `schema/denominateur.schema.json`.
- `scripts/build.py` — valide `data/`, calcule l'**indice C·P**, et génère `site/data.js`, les fragments, `site/couverture.{json,js}`, `site/communes-index.js`, `site/flux.js`. **Fichiers générés : jamais édités à la main, et non versionnés (issue #11)** — le déploiement Pages les régénère à chaque merge ; en local, lancer `build.py` avant d'ouvrir le site. ⚠️ **Une exception : `build.py` réécrit aussi le tableau de couverture de `README.md`** entre ses balises `<!-- couverture:debut/fin -->` — un fichier versionné, donc un diff à committer ou à annuler sciemment.
- `scripts/pipelines/` — pipelines rejouables (ADR-0002 : « on relit le script, pas les 35 000 nœuds ») : `fiches_communales_ofgl.py` (par département), `fiches_echelons_ofgl.py` (`--echelon`, qui **importe** du premier les listes de sous-postes pour qu'elles n'existent qu'une fois), `qui_percoit.py`, `qui_paie.py`, `ventiler_par_nature.py`, `qualifier_profondeur.py`, `alleger_sources.py`. Les deux pipelines OFGL **préservent les fiches existantes** : sans `--forcer`, relancer ne réécrit rien.
- `scripts/verifier_sources.py` (`--data`) et `scripts/verifiers/fond.py` (`--max`, défaut 40) — les moteurs réels de `sources.yml` et `verify-fond.yml`, lançables en local. `scripts/extract_plf.py` — extraction du PLF.
- `site/index.html` — site statique (D3 depuis cdnjs, zéro build front). **Quatre lentilles** : 💸 Dépenses · 💰 Recettes · 🔀 Flux · 🧾 Ma fiche de paie. Vue mobile dédiée sous 768 px (forage en liste, bottom sheet, barre d'onglets).
- `data-sources/raw/` — extraits bruts versionnés des API. **Ils font foi** : un brut absent est une erreur fatale, et `--telecharger` est refusé quand la variable d'environnement `CI` est posée (convention, pas verrou — seuls les deux pipelines OFGL l'implémentent ; les autres échouent sur un `FileNotFoundError` nu).
- `.github/workflows/` — `validate.yml` (bloquant, tourne sur tout), `sources.yml` (hygiène et tiers de confiance), `verify-fond.yml` (re-vérifie chaque montant modifié à sa source), `pages.yml` (déploiement).

## L'indice C·P (ADR-0006)

Le compteur affiché à côté du titre. **Deux nombres qui ne se moyennent jamais** :

- **C** — part des euros de l'univers APU représentés dans l'arbre ;
- **P** — profondeur atteinte sur l'échelle `P0`→`P6` (P0 agrégat · P1 politique · P2 entité nommée · P3 ligne budgétaire · P4 organisme · **P5 bénéficiaire nommé** · **P6 pièce justificative**).

Au 07/2026 : **C = 46,0 %** (837,6 Md€ couverts sur un univers de 1 819,9 Md€) et **P = 2,66** en dépenses ; **C = 42,1 %** (702,6 Md€ / 1 667,3 Md€) et **P = 2,00** en recettes. Les deux volets ont chacun leur C ET leur P — le P des recettes est plus bas parce que l'état A est plat (156 lignes, `niveaux: [P0, P1, P2]`). L'univers retenu est la **base brute** (`base_retenue: "brut"`), pas le consolidé publié (1 714,2 Md€) : 105,6 Md€ d'écart, qui déplacent C de plusieurs points.

**Règle anti-triche cardinale : on ne divise jamais un euro d'une comptabilité par un euro d'une autre.** Le coefficient d'un bloc se mesure dans un référentiel homogène (PLF ÷ PLF, OFGL ÷ OFGL) puis s'applique au poids SEC. Un bloc sans référentiel homogène compte **zéro**, même si l'arbre le documente. **Quatre blocs sur neuf sont dans ce cas, soit 978,6 Md€ en dépenses** : Sécu (682,5), ODAC (129,2), ODASS (120,8), ODAL (46,1).

**Cette règle est mécanique depuis l'ADR-0007.** Référentiel et arbre déclarent chacun leur `base_comptable` (`PLF` · `OFGL` · `CCSS` · `SEC`, énumération **fermée**), et `build.py` refuse : un référentiel muet, un référentiel en base `SEC` (circulaire — le poids l'est déjà, `c = 1` par construction), un arbre muet, et **toute divergence arbre ↔ référentiel**. Les quatre attaques ayant servi à la démontrer sont rejouées dans l'ADR-0007.

⚠️ **Sa limite, à ne pas surpromettre** : le verrou compare des **étiquettes et des montants déclarés**, il ne relit aucune source. Une revue adversariale a montré qu'une première version, sans les règles E et F, laissait passer +30,3 points de C en divisant simplement `total_eur` par deux — étiquette parfaitement honnête. Restent ouverts : un `total_eur` fabriqué mais plausible, une étiquette mensongère, un référentiel inventé sur un bloc à zéro. Le gain est que ces erreurs deviennent des **lignes explicites dans un diff** au lieu d'omissions invisibles. **La relecture humaine reste nécessaire.**

Deux corollaires contre-intuitifs, à ne pas redécouvrir à ses dépens :

- **Ingérer des fiches ne fait pas toujours monter C.** Les 11 394 CCAS et 97 SDIS relèvent du bloc `APUL.odal`, sans référentiel — leurs 9,31 Md€ sourcés et réconciliés comptent zéro. Le travail est fait, il n'est pas comptabilisé.
- **Un bloc à `c = 0` est absent de P autant que de C.** `comptes = c × poids_eur` : approfondir un bloc non raccordé ne fait bouger *aucun* des deux nombres. Vérifié — pousser tout l'arbre Sécu à P6 laisse P à 2,663, inchangé. Le comportement est voulu (sinon la faille fermée sur C se rouvrirait par P), mais il signifie qu'il est **inutile d'approfondir la Sécu, les ODAC, les ODASS ou les ODAL** tant que leur raccord n'existe pas.

Le corpus réellement présent pilote le numérateur ; `couvert_referentiel_eur` est une **assertion vérifiée** (au-delà de `max(1 €, 0,5 %)` d'écart, le build échoue). Toute PR qui ajoute ou retire des fiches **d'un bloc doté d'un référentiel** doit donc mettre ce nombre à jour.

## Commandes

```bash
python3 scripts/build.py --check              # validation + calcul C·P (ce que fait la CI) — n'écrit rien
python3 scripts/build.py                      # + régénération de site/ ET du tableau du README
python3 scripts/build.py --show <id>          # un nœud avec sa source résolue (ADR-0005)
python3 -m http.server -d site                # prévisualiser http://localhost:8000

python3 scripts/pipelines/fiches_communales_ofgl.py --departement 45 [--telecharger] [--forcer]
python3 scripts/pipelines/fiches_echelons_ofgl.py --echelon departements [--telecharger] [--forcer]
python3 scripts/pipelines/qualifier_profondeur.py --verifier   # dry-run — SANS --verifier, ÉCRIT dans data/
python3 scripts/verifier_sources.py           # hygiène des sources, en local
python3 scripts/verifiers/fond.py --max 40    # re-vérification des montants à la source
```

`build.py --check` sort en 0 mais émet **une vingtaine d'AVERTISSEMENT non bloquants** : ce n'est pas une régression de ta PR. La plupart sont des faux positifs sur montants négatifs (« somme des enfants (-4,295) > parent (-4,295) ») ; quelques-uns sont réels (`coll.depenses` / `coll.recettes` sans `source.maj`).

## État des données (07/2026)

- **État / dépenses** — PLF 2025 intégral, 823,0 Md€, 2 801 nœuds, missions → programmes → actions → sous-actions ventilées par titre LOLF. Tout `confirme`.
- **État / recettes** — les 156 lignes de l'état A, 588,4 Md€, 162 nœuds. Tout `confirme`.
- **Sécurité sociale** — comptes 2025 par branche (CCSS), 666,0 Md€ / 644,4 Md€.
- **Collectivités** — **56 491 fiches** : 34 877 communes, 1 266 intercommunalités, 97 départements, 17 régions, 8 743 syndicats, 11 394 CCAS/CIAS, 97 SDIS. Comptes 2024, réconciliés au centime par le pipeline (`centime()`, tolérance 0,01 €) ; à défaut de réconciliation, total seul sans ventilation.
- **Flux** — 9 flux entre administrations, dont le circuit UE bidirectionnel.
- **Total : 1 327 912 nœuds** · pack git 92,9 Mio. Généré par `build.py` : `site/data.js` ≈ 2,6 Mo, `site/communes-index.js` ≈ 3,5 Mo, et **`site/data/` ≈ 865 Mo** de fragments — prévoir la place avant un premier build local.
- **Compteur : C = 46,0 % · P = 2,66 (dépenses) — C = 42,1 % · P = 2,00 (recettes).** Un C et un P par volet, jamais moyennés.

## Pièges techniques connus

### Le piège majeur : le nom d'un agrégat ne dit pas son périmètre

**Toujours ouvrir la définition officielle d'un bloc AVANT de l'utiliser.** Cinq erreurs successives, toutes du même moule :

- « Communes » au sens OFGL ≠ « communes » au sens SEC : **S131311 inclut les EPCI**, et aucune table INSEE ne leur est dédiée. Un coefficient mesuré sur les seules communes était appliqué à un poids SEC contenant **71,2 Md€ d'EPCI non modélisés** : couverture surestimée d'**environ 3 points**, jusqu'à ce que les 1 266 intercommunalités soient ingérées et le référentiel élargi (20/07/2026).
- Les tables de passage INSEE **3.107** (État) et **3.108** (Sécu) existent bel et bien — mais convertissent un **solde**, jamais des flux. Elles échouent en outre pour deux raisons *distinctes* : 3.108 part du seul régime général (périmètre plus étroit), 3.107 part de l'**exécution constatée** quand l'arbre modélise le **PLF déposé** (prévision). D'où `raccord_publie: false` partout.
- L'OFGL ne publie que ~31 % du périmètre ODAL (CCAS et SDIS) : y poser un coefficient aurait refait la même erreur.
- « ODAC » (classification INSEE, ~700 unités) ≠ « **opérateurs de l'État** » (catégorie budgétaire, ~434 au jaune). Le jaune l'écrit lui-même — *« tous les opérateurs de l'État ne relèvent cependant pas de la liste des ODAC »*, ONF en exemple — et la LFI 2020 art. 179 l'oblige à publier les deux listes. **Les périmètres se croisent**, et une partie du résidu (agences de l'eau, SOLIDEO, sociétés de grands projets) relève d'`APUL.odal`, **un autre bloc du dépôt**.

- « ODASS » ≠ « hôpitaux publics ». S13142 comprend aussi les **hôpitaux privés financés par dotation globale**, les **œuvres sociales des organismes de sécurité sociale** et **France Travail hors indemnisation** (~6,9 Md€). L'INSEE le dit dans le titre même du tableau — « … **dont** hôpitaux, Pôle Emploi,**…** » — que le dépôt citait sous un nom raccourci qui effaçait l'avertissement.

**Le réflexe qui en découle : vérifier la contenance dans LES DEUX SENS, et ne jamais raccourcir le titre d'une source — il porte souvent l'avertissement.** Trois fois sur quatre, le projet n'a testé que l'inclusion supposée et a manqué le sens inverse.

### Mesurer git en poids d'arbre de travail est faux

Les 56 491 fiches pèsent **853 Mo sur disque** mais **92,9 Mio de packfile** — le JSON répétitif se compresse d'un facteur ~9. Un « mur de stockage » a été annoncé à tort sur cette confusion (issue #57). Mesure correcte : `git count-objects -vH`, jamais `du`.

### APIs

- **data.economie** (ODS Explore v2.1) : URL-encoder parenthèses et quotes (`sum%28cp%29`), sinon 400 silencieux. Gros volumes : `/exports/json` avec `curl --compressed`.
- **OFGL** : `exer` est un champ **date** → `year(exer)=2024`, jamais `exer="2024"`. Filtrer `type_de_budget="Budget principal"` sur les jeux non consolidés. Les jeux `-consolidee` incluent les budgets annexes.
- **Inspecter un jeu avec `group_by` : penser à la limite.** Une requête tronquée à 40 agrégats sur 60 a fait conclure à tort qu'un jeu ne publiait pas ses recettes.
- Dates de maj d'un jeu ODS : `metas.default.modified`.
- « Produit des cessions d'immobilisations » recouvre « Autres recettes d'investissement » chez ~4 % des communes → volontairement exclu.
- Comptes de CCAS : `fonctionnement + investissement ≠ total` chez **13,8 %** d'entre eux (1 574 fiches sur 11 394 ; 11,2 % en dépenses, 11,5 % en recettes). Le pipeline émet alors le **total seul**, sans ventilation, avec un nœud qui l'explique — plutôt qu'une ventilation fausse.

### Modèle

- Rupture M14→M57 (2024) dans les balances communales ; fusions de communes → passer par le COG INSEE millésimé.
- Le circuit recette→branche Sécu n'est PAS bijectif (TVA affectée, taxe sur les salaires, compensations) : ne jamais forcer une correspondance 1:1.
- `exer = 2024` est **codé en dur** dans les deux pipelines de collectivités, face à un univers 2025 (`ecart_millesime: true`). Dette déclarée.

### Shell

`zsh` : pas de word-splitting des variables non quotées (utiliser `read`/heredoc, jamais `set -- $var`). **`$?` après un pipe renvoie le code du dernier maillon**, pas celui du script — vérifier les codes de sortie sans pipe.

## Git / PR

- Branches : `data/<sujet>`, `site/<sujet>`, `docs/<sujet>`, `ci/<sujet>`, `fix/<sujet>`. Commits en français, impératif, préfixés.
- **Une PR = un sujet.** Corps de PR : source(s) utilisée(s), méthode, **et ce qui n'a PAS pu être vérifié**. La CI doit passer.
- **Revue humaine systématique**, jamais d'auto-merge.
- Ne jamais commiter de secrets ; le dépôt est public.

## Contraintes juridiques

- Données : Licence Ouverte 2.0 — mention de source obligatoire (faite nœud par nœud).
- Code : **AGPL-3.0**.
- **DSFR interdit** : composants, bleu France `#000091`, police Marianne et bloc République sont réservés aux sites de l'État. Le site suit les *principes* du DSFR sans le réutiliser (voir README).
- **Neutralité** : les `description` documentent les flux, jamais d'opinion sur leur opportunité. Aucune surface éditoriale ou narrative.

## Ce qui reste (issue #50)

Plus rien ne dépend d'un simple effort d'ingestion — tout ce qui manque relève d'une source non publiée :

| Bloc | Poids | Obstacle |
|---|---:|---|
| Régimes d'assurance sociale | 682,5 Md€ | raccord CCSS→SEC inexistant en flux |
| ODAC (opérateurs) | 129,2 Md€ | crédits publiés en PDF seulement |
| Hôpitaux (ODASS) | 120,8 Md€ | données ATIH non explorées |
| ODAL | 46,1 Md€ | 69 % du périmètre non publié (les 31 % ingérés comptent zéro) |

**Le raccord Sécu est de loin le levier le plus rentable** : ce bloc pèse **37,5 % de l'univers** à lui seul (682,5 / 1 819,9 Md€). Le raccorder porterait C de 46,0 % à ~83,5 % — davantage que les trois autres blocs réunis (296,1 Md€, soit 16,3 %).

Également ouvert : le millésime 2025, les pages `/perimetre` · `/plafond` · `/methode`, et `data/plafond-legal.json` — non livré tant qu'aucune de ses lignes n'a été vérifiée en montant, le sujet étant politiquement sensible.

## Référence documentaire

- `docs/adr/` — 7 ADR acceptés. **Les lire avant tout travail structurant.**
- `docs/etude-donnees.md` — inventaire des sources, granularités, licences, inconnues documentées avec contacts.
