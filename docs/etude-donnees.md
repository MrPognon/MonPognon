# Étude des données ouvertes — « Où va l'argent public en France ? »

*Étude préparatoire pour un site open source de visualisation des flux d'argent public (commune → État → Sécurité sociale ↔ fiche de paie). Vérifications effectuées le 7 juillet 2026.*

---

## Résumé exécutif

Toutes les briques de données existent pour construire le produit, mais **aucun projet actif ne les assemble** en un parcours citoyen unique (fiche de paie → commune → national). Le créneau est libre.

Trois constats structurants :

1. **La donnée est abondante et sous Licence Ouverte 2.0** (réutilisation libre, y compris commerciale, avec mention de source) pour l'essentiel : budget de l'État (data.economie.gouv.fr), finances locales (OFGL + balances DGFiP), protection sociale (DREES, Urssaf, Unédic, CNAM, CNAV, CNSA).
2. **Les règles de la fiche de paie ne sont PAS en open data officiel structuré** (le BOSS et l'Urssaf publient en HTML/PDF), mais deux moteurs open source officiels ou soutenus par l'État comblent ce vide : **`modele-social`** (Urssaf/beta.gouv, MIT, langage Publicodes avec explications en français) et **OpenFisca-France** (AGPL).
3. **Les inconnues sont identifiables et documentées** (voir §6) : exécution fine du budget de l'État après 2017, ventilation géographique des dépenses de l'État, budgets votés des communes, comptes de la Sécu en PDF seulement, Agirc-Arrco opaque. Pour chacune, il existe un contact public et une voie de recours (CADA / madada.fr).

---

## 1. Budget de l'État et recettes fiscales

### 1.1 Ce qui existe

| Donnée | Source / jeu | Granularité | Fréquence | API |
|---|---|---|---|---|
| Dépenses prévues PLF/LFI (missions → programmes → actions → sous-actions, nomenclature LOLF) | data.economie.gouv.fr, série `plf25-depenses-2025-selon-destination` (2 404 lignes) et croisement destination × nature ; séries remontant à 2011-2012 | Action budgétaire | Annuelle (octobre, dépôt du PLF) | ODS Explore v2.1 |
| Recettes prévues (IR, IS, TVA, TICPE… ligne à ligne de l'état A) | `plf25-recettes-du-budget-general` (156 lignes) + comptes spéciaux, budgets annexes | Ligne de recette | Annuelle | ODS Explore v2.1 |
| Exécution mensuelle (solde, dépenses par ministère/titre, recettes par catégorie) | `situations-mensuelles-budgetaires-series-longues` (nouveauté mars 2025, données 2013→auj., dernière modif. 03/07/2026) + Situation mensuelle de l'État (PDF) | Ministère / titre | Mensuelle | ODS Explore v2.1 |
| Comptabilité générale de l'État | `balances_des_comptes_etat` (CGE 2016-2025, 517 489 lignes) + dataviz budget.gouv.fr | Compte | Annuelle | ODS Explore v2.1 |
| Budget vert (cotation environnementale des dépenses) | `plf-2026-budget-vert` (1 816 lignes : exécution 2024, LFI 2025, PLF 2026) | Dépense/action | Annuelle | ODS Explore v2.1 |
| IR par commune | IRCOM (DGFiP), maj vérifiée 26/05/2026 | **Commune** | Annuelle | Tabular API data.gouv |
| Taxes affectées, dépenses fiscales | Voies et moyens T1/T2 en data jusqu'au PLF 2024 ; PDF ensuite | Taxe / dispositif | Annuelle | — |
| Opérateurs de l'État | Jaune « Opérateurs » PLF 2026 (liste des 431 opérateurs) | Opérateur | Annuelle | — |
| Cadrage macro toutes administrations (APUC/APUL/ASSO) | INSEE, Comptes des administrations publiques (HVD) ; dépenses par fonction COFOG 1995-2024 | Sous-secteur × fonction | Annuelle (mai) | Melodi, BDM ; alt. Eurostat SDMX |
| Exécution détaillée récente (source de substitution) | Cour des comptes : rapport « Le budget de l'État en N » + ~60 notes d'exécution budgétaire par mission | Mission | Annuelle | PDF |

URLs clés : catalogue budget https://data.economie.gouv.fr/explore/?refine.theme=BUDGET+DE+L'ETAT · https://www.budget.gouv.fr · IRCOM https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom · INSEE COFOG https://www.insee.fr/fr/statistiques/8574707?sommaire=8574832 · Cour des comptes https://www.ccomptes.fr/fr/cour-des-comptes/nous-decouvrir/donnees-publiques

### 1.2 Granularité géographique des recettes (constat important)

- IR : **communal** (IRCOM). Fiscalité directe locale : **communal** (REI).
- **TVA, IS, TICPE : national uniquement.** Aucune ventilation territoriale publiée (secret fiscal pour l'IS ; non-pertinence conceptuelle pour la TVA). Le site devra l'assumer et l'expliquer.

---

## 2. Finances locales (communes, EPCI, départements, régions)

### 2.1 Architecture recommandée (4 couches)

1. **OFGL — socle** (https://data.ofgl.fr, API ODS) : agrégats propres et documentés par collectivité, 2012/2017→2024. Jeux : `ofgl-base-communes`, versions consolidées (BP + budgets annexes), `ofgl-base-ei` (ensembles intercommunaux), départements, régions, syndicats, et **`dotations-communes` (montants ET critères DGF 2018-2026)** — la donnée la plus fraîche du paysage.
2. **Balances comptables DGFiP — drill-down** (data.economie.gouv.fr, depuis 2010) : ligne = budget (SIRET, donc budgets annexes inclus) × compte M14/M57. Variante essentielle : **présentation croisée nature-fonction** (enseignement, sport, voirie… — 2012→2023, 2024 attendu) pour répondre à « à quoi sert l'argent ».
3. **Comptes individuels des collectivités** (impots.gouv.fr/cll + CSV) : ~100 indicateurs pré-calculés dont **euros/habitant et moyennes de strate** — parfait pour la comparaison citoyenne. Communes depuis 2000.
4. **REI — fiscalité locale** (data.gouv, millésimes depuis 1982) : bases, taux et produits par taxe (TFPB, THRS, CFE, TEOM, GEMAPI…) et par niveau, par commune.

### 2.2 Référentiels pivots

- Code officiel géographique INSEE (fusions de communes !) : https://www.insee.fr/fr/information/2560452
- geo.api.gouv.fr (sélecteur de commune, contours, population — sans clé)
- BANATIC (périmètres et compétences EPCI/syndicats) : https://www.banatic.interieur.gouv.fr
- Table de passage code INSEE ↔ SIREN/SIRET (Datactivist) : https://www.data.gouv.fr/datasets/identifiants-des-collectivites-territoriales-et-leurs-etablissements

### 2.3 Flux État ↔ collectivités à représenter

DGF et dotations (OFGL/DGCL, critères publiés), dotations d'investissement DETR/DSIL/DSID/Fonds vert (granularité **projet subventionné**), fractions de TVA transférées (remplaçant la CVAE depuis 2023), FPIC, FNGIR, allocations compensatrices d'exonérations. **Aucun jeu unique ne consolide ces flux** : reconstruction nécessaire à partir des balances (comptes 73211, 739xx…), du REI et des fichiers critères DGCL.

---

## 3. Protection sociale et fiche de paie

### 3.1 Le moteur de calcul (brut → net → affectation)

| Brique | Producteur | Licence | Rôle proposé |
|---|---|---|---|
| **`modele-social`** (npm) + Publicodes | Urssaf / beta.gouv (produit officiel mon-entreprise) | MIT | Moteur front : toutes les cotisations 2026 (maladie, vieillesse, Agirc-Arrco T1/T2, CEG/CET, CSG/CRDS, PAS), **chaque règle avec explication en français** |
| **OpenFisca-France** | Communauté / héritage Etalab | AGPL-3.0 | Validation croisée, backend, historique des paramètres en YAML |
| **Barèmes IPP** | Institut des politiques publiques | Ouverte | Validation + profondeur historique (taux depuis 1945) |
| BOSS (boss.gouv.fr) + urssaf.fr | DSS / Urssaf | — | Source « opposable » de contrôle — **HTML/PDF uniquement, pas d'API** |

### 3.2 Où va chaque euro prélevé (recettes/dépenses par branche)

| Donnée | Source | Format | Limite |
|---|---|---|---|
| Recettes/dépenses/soldes par branche (maladie, AT-MP, vieillesse, famille, autonomie) et par type de recette | Rapports CCSS, 2×/an : https://www.securite-sociale.fr/la-secu-en-detail/comptes-de-la-securite-sociale/rapports-de-la-commission | **PDF** | LA référence, mais extraction de tableaux à automatiser |
| Tableaux d'équilibre, impôts affectés (fraction TVA, taxe sur les salaires), compensation des exonérations | PLFSS Annexe 3 (assemblee-nationale.fr) | **PDF** | Indispensable pour boucler « chaque euro » |
| Prestations/ressources par risque × régime, 1959-2023 | DREES, Comptes de la protection sociale : https://data.drees.solidarites-sante.gouv.fr | CSV/API ODS | Décalage N-2 ; nomenclature ESSPROS ≠ branches |
| Recouvrement, exonérations par mesure/secteur/département | https://open.urssaf.fr | CSV/API ODS | Pas les recettes par branche destinataire |
| Dépenses maladie | Open DAMIR + data.ameli.fr | CSV (Go) / API | DAMIR sans API, très volumineux |
| Retraites | CNAV (data.assuranceretraite.fr) + COR (Excel) | XLSX/API | Compensations inter-régimes en PDF |
| Chômage | https://data.unedic.org (recettes/dépenses depuis 2011) | CSV/API ODS | Très bonne transparence |
| Autonomie | https://data-autonomie.cnsa.fr (lancé 2025) | CSV/API ODS | Récent |
| Famille | https://data.caf.fr | CSV/API ODS | Dépenses par nature à vérifier |
| Retraite complémentaire | Agirc-Arrco : Excel non normalisés, communiqués | XLSX/PDF | **Point faible : pas de portail, pas d'API, licence indéterminée** |

---

## 4. Projets existants (à réutiliser, pas à réinventer)

**Officiels** : « À quoi servent mes impôts ? » (economie.gouv.fr/aqsmi, pédagogique, non open source) · dataviz du Compte général de l'État et des données de performance (budget.gouv.fr) · comptes des collectivités impots.gouv.fr/cll · « En avoir pour mes impôts » (2023, non pérennisé).

**Open source réutilisables** : OpenFisca · LexImpact (Assemblée nationale, AGPL) · mon-entreprise/Publicodes (MIT) · TAXIPP (IPP).

**Citoyens** : decomptes-publics.fr (comptes de ma commune) · « Budget Ouvert » (treemap PLF) · Regards Citoyens (leçon de soutenabilité : équipe bénévole épuisée, appel à repreneurs).

**Étranger** : USAspending.gov (référence mondiale, open source, API) · OpenSpending / Where Does My Money Go (UK — pionnier, en sommeil) · OffenerHaushalt.de (Allemagne, dépendant du bénévolat).

**Constat : personne ne fait le parcours complet fiche de paie ↔ commune ↔ national. C'est le positionnement du projet.**

---

## 5. Licences et cadre juridique

- **Licence Ouverte Etalab 2.0** sur la quasi-totalité des données : réutilisation libre avec mention « Source : [producteur], [date] ». Compatible open source et usage commercial.
- **Loi République numérique (2016)** : open data par défaut obligatoire pour les collectivités > 3 500 hab. et > 50 agents — mais seulement ~5-8 % publient. Argument juridique pour réclamer les données manquantes.
- **Licence du projet** : les briques amont imposent leurs termes — OpenFisca/LexImpact en AGPL-3.0 (copyleft réseau), modele-social en MIT. **Recommandation : AGPL-3.0** pour le projet (compatibilité maximale + garantie que les forks restent ouverts).

---

## 6. Les inconnues — ce qui n'existe PAS, et qui contacter

**✅ Fait (issue #19) : chacune de ces 13 inconnues vit désormais dans les données** — un nœud ❓ dans `data/`, visible sur le site, avec `inconnu.quoi` et `inconnu.contact` (et `inconnu.url` quand une demande madada est déposée, voir #6). **La vérité opérationnelle est dans les nœuds** ; ce tableau reste la référence méthodologique d'origine.

Correspondance : 1 → `etat.depenses.inconnu-execution` · 2 → `etat.depenses.inconnu-infra-annuel` · 3 → `etat.depenses.inconnu-geo` · 4 → `etat.recettes.inconnu-territorialise` · 5 → `coll.depenses.inconnu-bp` · 6 → `coll.depenses.inconnu-fonction` · 7 → `coll.depenses.inconnu-syndicats` · 8 → `secu.depenses.inconnu-ccss` · 9 → `secu.recettes.inconnu-taux` · 10 → `secu.depenses.inconnu-agirc` · 11 → `etat.qui-percoit.inconnu-consolide` · 12 → `etat.qui-percoit.inconnu-decp` · 13 → `etat.depenses.inconnu-plf2026`

| # | Inconnue | Détail | Contact public / recours |
|---|---|---|---|
| 1 | **Exécution fine du budget de l'État après 2017** | Les données machine-readable mission/programme/action s'arrêtent au PLR 2017 ; depuis : PDF (RAP) et notes de la Cour des comptes | Direction du Budget via https://data.economie.gouv.fr/pages/contact/ ; demande CRPA à la PRADA du ministère puis CADA |
| 2 | **Exécution infra-annuelle par mission** | La situation mensuelle ne donne que des agrégats par ministère/titre ; les données Chorus fines ne sont pas publiées | Direction du Budget + AIFE (opératrice de Chorus) |
| 3 | **Ventilation géographique des dépenses de l'État** | Aucune donnée « dépenses de l'État dans mon département » ; l'ancien jaune « effort de l'État en régions » a disparu | DB + DGFiP ; manque documenté par la Cour des comptes |
| 4 | **TVA, IS, TICPE territorialisés** | Secret fiscal / non publié | DGFiP — Département des études et statistiques fiscales ; chercheurs : CASD |
| 5 | **Budgets votés (primitifs) des communes** | Les XML TOTEM/Actes budgétaires ne sont pas centralisés en open data ; on ne voit que l'exécuté à N+1 | DGCL (collectivites-locales.gouv.fr) ; chaque commune (loi République numérique) ; schéma SCDL Budget |
| 6 | **Détail fonctionnel des petites communes** | Présentation nature-fonction obligatoire seulement ≥ 3 500 hab. → « à quoi sert l'argent » indisponible pour ~90 % des communes | DGFiP / DGCL |
| 7 | **Flux commune⇄EPCI⇄syndicats** | Clés de répartition des contributions aux syndicats non publiées | DGCL (BANATIC) ; OFGL (formulaire data.ofgl.fr, réactif) |
| 8 | **Comptes de la Sécu structurés** | Rapports CCSS et annexe 3 PLFSS en PDF uniquement | DSS (securite-sociale.fr) — le maillon le moins ouvert |
| 9 | **Taux de cotisations en open data officiel** | BOSS/Urssaf en HTML ; les moteurs open source ne sont pas « opposables » | DSS via boss.gouv.fr ; issues GitHub betagouv/mon-entreprise ; contact@openfisca.org |
| 10 | **Agirc-Arrco** (~101 Md€ de cotisations 2024) | Organisme paritaire privé chargé d'un service public : en principe soumis au CRPA, publie peu et sans licence claire | Direction Agirc-Arrco ; demande CADA (applicable aux organismes privés chargés d'un service public) |
| 11 | **Subventions publiques consolidées** (~23 Md€/an) | Le jaune « associations » ne couvre que l'État ; rien de consolidé État + collectivités + Sécu | Direction du Budget ; question parlementaire |
| 12 | **Commande publique (DECP)** | Données consolidées de qualité défaillante (doublons, identifiants manquants) | AIFE / data.gouv.fr, nouveau format unifié depuis 01/2024 |
| 13 | **PLF 2026 en data** | Au 07/07/2026, seul le budget vert est publié ; les séries dépenses/recettes PLF 2026 manquent | DB via data.economie |

### Procédure de recours (à intégrer au site, bouton « réclamer cette donnée »)

1. Demande écrite à la PRADA de l'administration → silence 1 mois = refus implicite.
2. Saisine CADA dans les 2 mois : https://www.cada.fr/formulaire-de-saisine
3. **madada.fr** : plateforme associative qui publie les demandes — idéal pour tracer publiquement les réclamations du site.
4. Discussion publique sur le jeu de données concerné sur data.gouv.fr.

---

## 7. APIs — récapitulatif technique

| API | Base | Couvre |
|---|---|---|
| ODS Explore v2.1 — data.economie | https://data.economie.gouv.fr/api/explore/v2.1/ | Budget État, balances communes, comptes individuels, fiscalité |
| ODS Explore v2.1 — OFGL | https://data.ofgl.fr/api/explore/v2.1/ | Agrégats collectivités, dotations |
| geo.api.gouv.fr | https://geo.api.gouv.fr | Communes, EPCI, population, contours (sans clé) |
| Tabular API data.gouv (bêta) | https://tabular-api.data.gouv.fr/api | REI, IRCOM, CSV divers |
| Melodi / BDM (INSEE) | https://api.insee.fr/melodi/ | Comptes nationaux, séries macro |
| ODS — DREES, Urssaf, Unédic, ameli, CNSA, CAF | portails respectifs | Protection sociale |
| API mon-entreprise (Urssaf) | https://mycompanyinfrance.urssaf.fr/developer/api | Calcul fiche de paie (REST, sans auth) |
| OpenFisca | auto-hébergement recommandé | Simulation socio-fiscale |

---

## 8. Recommandations pour la v1

1. **Périmètre v1** : sélecteur de commune (geo.api.gouv.fr) + fiche financière OFGL/comptes individuels + décomposition fiche de paie via `modele-social` + cadrage national INSEE/PLF. Les flux fins (FPIC, syndicats) en v2.
2. **Pipeline de données versionné** (dépôt Git séparé) : extraction annuelle des sources, tables de passage M14→M57 et ESSPROS→branches, extraction automatisée des PDF CCSS — chaque transformation documentée et re-jouable (crédibilité = reproductibilité).
3. **Chaque chiffre affiché porte sa source cliquable** (jeu de données + millésime + licence) et chaque inconnue son contact et son statut de réclamation (lien madada.fr).
4. **Attention à la non-bijectivité** : le circuit cotisation→branche→dépense n'est pas 1:1 (TVA affectée à la Sécu ~28 % de la TVA, taxe sur les salaires, compensations, transferts inter-régimes). Prévoir un nœud « transferts et impôts affectés » explicite plutôt que de forcer des correspondances fausses.
5. **Millésimes hétérogènes** : exécuté communal à N+1, REI à N+18 mois, DREES à N-2, DGF de l'année en cours. Afficher l'année de chaque donnée, ne jamais mélanger silencieusement.
6. **Gouvernance** : prévoir dès le départ la soutenabilité (leçon Regards Citoyens) — association, dons, contributions ; licence AGPL-3.0.

---

*Rapport généré le 07/07/2026. Toutes les URLs ont été vérifiées à cette date via data.gouv.fr (API), data.economie.gouv.fr et recherche web. Ordres de grandeur donnés à titre indicatif — à recalculer depuis les sources lors de la construction du pipeline.*
