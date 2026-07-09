# Documents sources versionnés — la politique des sources sans URL publique

> **Le principe** (issue #14) : une source n'a pas besoin d'une URL d'origine, mais elle doit être
> **publiquement consultable et vérifiable par un tiers**. C'est la *publicité* du document qui compte,
> pas son mode d'obtention.

Certaines données légitimes arrivent sans URL : réponse à une demande CADA reçue **par email ou
courrier**, budget non mis en ligne, délibération papier scannée, document transmis par un service
public. Les refuser casserait le circuit « réclamer → obtenir → publier » ; les accepter sans cadre
ouvrirait la porte aux documents forgés. D'où deux circuits :

## Circuit 1 — madada.fr (à privilégier, toujours)

[madada.fr](https://madada.fr) publie **les demandes ET les réponses** : une réponse CADA qui y transite
devient une page publique, horodatée par un tiers neutre. → `source.url` = l'URL madada de la réponse,
`producteur` = l'administration répondante. **Le document privé redevient une source publique ordinaire**,
rien d'autre à faire. (Rappel #6 : les demandes se font **en votre nom propre**, jamais au nom du projet.)

## Circuit 2 — le document versionné ici (quand madada n'a pas été utilisé)

1. **Caviardez d'abord** : aucune donnée personnelle ne doit entrer dans ce dépôt public — nom, adresse,
   email et signature du demandeur, coordonnées d'agents non publiques. En cas de doute, caviardez.
2. Déposez le document : `data-sources/documents/<producteur>/<annee>-<slug>.pdf`
   (ex. `mairie-chateauneuf-sur-loire/2026-deliberation-subventions.pdf`).
3. Remplissez sa **provenance** à côté : `<annee>-<slug>.provenance.md` — copiez
   [`MODELE.provenance.md`](MODELE.provenance.md). Sans provenance complète, le document sera refusé.
4. Dans le nœud, `source.url` pointe le fichier du dépôt :
   `https://github.com/MrPognon/MonPognon/blob/main/data-sources/documents/<producteur>/<fichier>.pdf`
   (le vérificateur de sources reconnaît les URLs du dépôt lui-même).
5. Ouvrez la PR : le document, sa provenance et les nœuds qui le citent, ensemble.

## Le niveau de confiance (quel statut ?)

Un document versionné avec provenance déclarative reste **plus faible** qu'une publication officielle
en ligne — un PDF peut être forgé. Règles :

- **`confirme`** seulement si le document est **authentifiable** : en-tête et signature de
  l'administration, référence d'acte recoupable (n° de délibération, référence de saisine CADA),
  ou cohérence avec une donnée centralisée (balances DGFiP, OFGL…) ;
- au moindre doute d'un relecteur : **`estime`**, avec la méthode en `description` — et idéalement un
  re-dépôt via madada pour officialiser ;
- quand une source **centralisée** existe pour le même chiffre, elle **prime** : le document local sert
  au contexte, pas à contredire silencieusement la source nationale (en cas de contradiction réelle →
  [contestation](../../.github/ISSUE_TEMPLATE/contester-une-donnee.md), l'écart s'affiche).

## Ce que la revue vérifiera

- [ ] Caviardage complet (zéro donnée personnelle)
- [ ] Provenance remplie (qui, quand, quelle administration, quel canal, quelle référence)
- [ ] Statut cohérent avec l'authentifiabilité
- [ ] Le nœud cite la **page précise** du document dans `source.nom`
