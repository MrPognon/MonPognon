#!/usr/bin/env python3
"""Valide les fichiers data/ et génère site/data.js.
Usage : python3 scripts/build.py [--check]        validation seule, pour la CI
        python3 scripts/build.py --show <id>      affiche un nœud, source résolue (ADR-0005)"""
import json, sys, glob, os, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUTS = {"confirme", "estime", "inconnu"}
errors, warnings = [], []

def resoudre_sources(node, path, parent_src=None):
    """Héritage de la source champ par champ, en descendant (ADR-0005).
    Un nœud sans source hérite tout ; une source partielle hérite des champs
    manquants ; la racine du fichier doit être complète (ancre). Après cette
    passe, chaque nœud porte sa source résolue — c'est elle qui est validée,
    générée dans data.js et les fragments, et affichée sur le site."""
    declaree = node.get("source")
    if parent_src is None and not declaree:
        errors.append(f"{path}: la racine du fichier doit porter une source complète — ancre de l'héritage ({node.get('id','?')})")
        return
    resolue = {**(parent_src or {}), **(declaree or {})}
    if "source" in node:
        node["source"] = resolue          # la clé garde sa position d'origine
    else:                                  # clé absente : l'insérer AVANT 'enfants'
        cles = list(node.keys())
        node["source"] = resolue
        if "enfants" in cles:
            for k in cles[cles.index("enfants"):]:
                node[k] = node.pop(k)      # repousse enfants (et la suite) après source
    for c in node.get("enfants", []):
        resoudre_sources(c, path, node["source"])

def validate(node, path, seen_ids):
    for req in ("id", "label", "statut", "source", "enfants"):
        if req not in node:
            errors.append(f"{path}: champ requis manquant '{req}' (nœud {node.get('id','?')})"); return
    if node["id"] in seen_ids: errors.append(f"{path}: id dupliqué {node['id']}")
    seen_ids.add(node["id"])
    if node["statut"] not in STATUTS: errors.append(f"{path}: statut invalide '{node['statut']}' ({node['id']})")
    if node["statut"] == "inconnu" and "inconnu" not in node:
        errors.append(f"{path}: statut 'inconnu' sans bloc 'inconnu' (qui contacter ?) ({node['id']})")
    src = node["source"]
    for req in ("nom", "url", "producteur", "consulte_le"):
        if not src.get(req): errors.append(f"{path}: source.{req} manquant ({node['id']})")
    maj = src.get("maj")
    if maj is not None and not (isinstance(maj, str) and len(maj) == 10 and maj[4] == "-" and maj[7] == "-"):
        errors.append(f"{path}: source.maj doit être au format AAAA-MM-JJ ou null ({node['id']})")
    if node.get("montant") is not None and maj is None:
        warnings.append(f"{path}: montant sans date de mise à jour de la source (source.maj) ({node['id']})")
    m = node.get("montant")
    if m is not None and not isinstance(m, (int, float)): errors.append(f"{path}: montant non numérique ({node['id']})")
    if m is not None and node.get("annee") is None: warnings.append(f"{path}: montant sans année ({node['id']})")
    kids = [c for c in node["enfants"] if c.get("montant")]
    if m and kids:
        s = sum(c["montant"] for c in kids)
        if s > m * 1.02:
            warnings.append(f"{path}: somme des enfants ({s:,.0f}) > parent ({m:,.0f}) de plus de 2 % ({node['id']})")
    for c in node["enfants"]: validate(c, path, seen_ids)

METHODE_COUVERTURE = (
    "Chaque euro du montant racine d'un arbre est attribué au statut du nœud le plus profond qui le porte : "
    "un total confirmé dont la ventilation fine est estimée compte comme estimé — le baromètre mesure la "
    "profondeur réelle du sourçage, pas la surface. Allocation descendante : les enfants à montant positif "
    "reçoivent leur montant (au pro-rata si leur somme dépasse le parent, cas des transferts internes) ; le "
    "reliquat non détaillé reste porté par le parent. Les montants négatifs (nœuds de neutralisation) sont "
    "exclus de l'allocation. Les arbres ne sont JAMAIS additionnés entre eux (transferts inter-administrations : "
    "TVA affectée, dotations…) — chaque périmètre se lit seul."
)


METHODE_CP = (
    "Indice C·P (ADR-0006) — deux nombres qui ne se moyennent JAMAIS. "
    "C = COUVERTURE DE PÉRIMÈTRE : part des euros de l'univers des administrations publiques "
    "(dénominateur INSEE, base brute) représentés dans l'arbre. Pour chaque bloc, le coefficient de "
    "couverture est mesuré À L'INTÉRIEUR d'un référentiel de comptage homogène (PLF ÷ PLF, OFGL ÷ OFGL), "
    "puis appliqué au poids en comptabilité nationale : on ne divise jamais un euro d'une comptabilité "
    "par un euro d'une autre. Un bloc sans référentiel homogène compte zéro, même si l'arbre le documente. "
    "P = PROFONDEUR : niveau moyen atteint sur l'échelle de destination P0→P6, calculé sur les SEULS euros "
    "couverts. P0 agrégat non ventilé · P1 politique publique · P2 programme ou entité nommée · "
    "P3 ligne budgétaire fine · P4 organisme destinataire · P5 bénéficiaire final nommé et rattaché à sa "
    "ligne payeuse · P6 pièce justificative. Un cran qui décrit COMMENT l'argent est dépensé (titre LOLF, "
    "nature de dépense) et non À QUI il va n'avance pas P : la table `niveaux` de chaque fichier le déclare "
    "par un null. La répartition par niveau vient des proportions internes de l'arbre, jamais d'une "
    "conversion entre comptabilités. C mesure la largeur, P la finesse : ni l'un ni l'autre ne mesure "
    "l'exactitude des montants — le baromètre de qualité de source répond à cette question-là."
)

NIVEAUX_P = ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]

# ── Bases comptables (ADR-0007) ───────────────────────────────────────────────
# La règle anti-triche de l'ADR-0006 (« on ne divise jamais un euro d'une
# comptabilité par un euro d'une autre ») était jusqu'ici un garde-fou éditorial :
# indice_cp() divisait sans jamais comparer les bases. Ces constantes et les
# quatre règles qui les exploitent rendent la promesse mécanique.
#
# L'énumération est FERMÉE À DESSEIN. Ajouter une base est une décision qui doit
# passer par une relecture, pas un effet de bord d'une PR de données : c'est
# précisément par un référentiel d'une autre comptabilité que la faille s'ouvrait.
BASES_COMPTABLES = {
    "PLF": "comptabilité budgétaire de l'État (LOLF, crédits de paiement)",
    "OFGL": "comptes locaux publiés par l'Observatoire des finances et de la gestion publique locales",
    "CCSS": "comptes de la Commission des comptes de la Sécurité sociale",
    "SEC": "comptabilité nationale (SEC 2010) — INTERDITE comme référentiel, voir plus bas",
}
# Le poids d'un bloc est TOUJOURS en SEC. Un référentiel lui aussi en SEC rendrait
# le coefficient tautologique (on diviserait le poids par lui-même, c = 1 par
# construction) : le bloc compterait plein sans qu'aucun euro soit modélisé.
# C'est le piège du tableau INSEE 3.204 relevé sur les ODAC.
BASE_INTERDITE_EN_REFERENTIEL = "SEC"


def valider_bases_comptables(arbres, denominateurs):
    """Règle du référentiel homogène, version mécanique (ADR-0007).

    Vérifie que le NUMÉRATEUR et le DÉNOMINATEUR d'un coefficient relèvent bien
    de la même comptabilité. Sans ce contrôle, on pouvait brancher un référentiel
    DREES sur un arbre CCSS, gagner trente points de couverture, et passer la CI
    en silence — c'est une attaque qui a été démontrée, pas une hypothèse."""
    for volet, denom in sorted(denominateurs.items()):
        # base attendue pour chaque bloc doté d'un référentiel
        base_du_bloc = {}
        for seg in denom["segments"]:
            for ss in seg["sous_segments"]:
                ref = ss.get("referentiel_comptage")
                if ref and ref.get("base_comptable"):
                    base_du_bloc[ss["code"]] = ref["base_comptable"]

        for node in arbres:
            bloc = node.get("bloc_univers")
            if not bloc or node.get("volet") not in (volet, "mixte"):
                continue
            attendue = base_du_bloc.get(bloc)
            if attendue is None:
                continue          # bloc sans référentiel : il compte zéro, rien à vérifier
            portee = node.get("base_comptable")
            if portee != attendue:
                errors.append(
                    f"{node['id']}: base comptable « {portee} » face à un référentiel "
                    f"« {attendue} » pour le bloc {bloc} ({volet}). Un coefficient ne se "
                    f"mesure qu'à l'intérieur d'une même comptabilité (ADR-0006 §3, "
                    f"ADR-0007) : corriger l'arbre, ou retirer le référentiel du bloc.")


def niveau_effectif(niveaux, prof):
    """Niveau de destination d'un euro porté à cette profondeur JSON : le dernier
    cran non nul à ou au-dessus de lui (un null n'avance pas l'axe destination)."""
    for p in range(min(prof, len(niveaux) - 1), -1, -1):
        if niveaux[p]:
            return niveaux[p]
    return "P0"


def indice_cp(arbres, denom):
    """Calcule C et P (ADR-0006). `arbres` : tous les nœuds racines porteurs d'un
    bloc_univers ; `denom` : le dénominateur du volet dépenses."""
    # 1) proportions par niveau de destination, à l'intérieur de chaque bloc
    volet = denom.get("volet", "depenses")
    euros_bloc, reel = {}, {}
    for node in arbres:
        bloc = node.get("bloc_univers")
        if not bloc:
            continue
        # Un arbre ne compte que dans SON volet : dépenses et recettes se mesurent
        # contre deux dénominateurs distincts et ne doivent jamais se mélanger.
        v = node.get("volet")
        if v not in (volet, "mixte"):
            continue
        niveaux = node.get("niveaux") or []
        # « mixte » = les deux volets sous une même racine (fiche communale, ADR-0004 :
        # le montant racine est null car dépenses et recettes ne s'additionnent pas).
        # On analyse alors le volet demandé, en décalant la profondeur d'un cran.
        cible, decalage = node, 0
        if v == "mixte":
            cible = next((c for c in node.get("enfants", []) if c["id"].endswith("." + volet)), None)
            decalage = 1
        if cible is None:
            continue
        # Somme RÉELLEMENT présente dans le corpus, exprimée dans le référentiel de
        # comptage du bloc. C'est elle qui alimente le numérateur de C : sans cela,
        # l'indice serait piloté par un nombre saisi à la main dans le dénominateur
        # et resterait identique si tout le corpus disparaissait.
        reel[bloc] = reel.get(bloc, 0.0) + (cible.get("montant") or 0.0)
        d = euros_bloc.setdefault(bloc, {})
        for prof, euros in couverture(cible)["profondeurs"].items():
            n = niveau_effectif(niveaux, int(prof) + decalage)
            d[n] = d.get(n, 0.0) + euros

    # 1 bis) P5 — les euros dont on connaît le bénéficiaire final ET la ligne payeuse.
    # Ils vivent dans les vues transverses (non sommées), mais désignent des euros
    # DÉJÀ comptés dans l'arbre du payeur : on les y RECLASSE, on ne les ajoute jamais.
    id_vers_bloc = {}
    for node in arbres:
        bloc = node.get("bloc_univers")
        # même filtre de volet que ci-dessus : une subvention versée depuis une ligne
        # de DÉPENSE ne doit jamais reclasser des euros du volet recettes.
        if not bloc or node.get("volet") not in (volet, "mixte"):
            continue
        def indexer(n):
            id_vers_bloc[n["id"]] = bloc
            for c in n.get("enfants", []):
                indexer(c)
        indexer(node)

    trace = {}
    def collecter_p5(n):
        cible = n.get("rattachement_id")
        if cible and n.get("identifiant") and isinstance(n.get("montant"), (int, float)):
            b = id_vers_bloc.get(cible)
            if b:
                trace[b] = trace.get(b, 0.0) + n["montant"]
        for c in n.get("enfants", []):
            collecter_p5(c)
    for node in arbres:
        collecter_p5(node)

    for bloc, montant in trace.items():
        d = euros_bloc.get(bloc)
        if not d:
            continue
        # on ne peut pas tracer plus d'euros que la ligne payeuse n'en porte :
        # le reclassement part des niveaux les plus profonds déjà atteints.
        sous = sorted((k for k in d if NIVEAUX_P.index(k) < 5), key=lambda k: -NIVEAUX_P.index(k))
        reste = min(montant, sum(d[k] for k in sous))
        for niv in sous:
            pris = min(d[niv], reste)
            d[niv] -= pris
            d["P5"] = d.get("P5", 0.0) + pris
            reste -= pris
            if reste <= 0:
                break

    # 2) C, et ventilation des euros d'univers par niveau
    univers = denom["total_brut_eur"]
    numerateur = raccorde = 0.0
    histo_univers = {n: 0.0 for n in NIVEAUX_P}
    histo_couvert = {n: 0.0 for n in NIVEAUX_P}
    blocs = []
    for seg in denom["segments"]:
        for ss in seg["sous_segments"]:
            ref, declare = ss.get("referentiel_comptage"), ss.get("couvert_referentiel_eur")
            present = reel.get(ss["code"])
            # Règle du référentiel homogène (ADR-0006) : sans référentiel, la couverture
            # est nulle même si l'arbre documente le bloc — cas du raccord Sécu manquant.
            if ref is None or present is None:
                c = 0.0
            else:
                c = present / ref["total_eur"]
                # ADR-0007 — un coefficient > 1 signifie que le corpus dépasse son propre
                # référentiel. C'est toujours faux : référentiel sous-dimensionné, ou corpus
                # hors périmètre. Sans ce plancher, `total_eur` reste un nombre libre — le
                # diviser par deux double le coefficient et gonfle C de trente points sans
                # qu'aucune base_comptable ne soit mensongère. Attaque vérifiée le 21/07/2026.
                if c > 1.005:
                    errors.append(f"dénominateur — {ss['code']} : coefficient {c:.4f} > 1 — le corpus "
                                  f"présent ({present:.2f} €) dépasse son référentiel de comptage "
                                  f"({ref['total_eur']:.2f} €). Soit le référentiel est sous-dimensionné, "
                                  f"soit l'arbre porte des euros hors de son périmètre (ADR-0007).")
                # La valeur déclarée n'est plus la source du calcul, mais elle reste une
                # ASSERTION VÉRIFIÉE : si elle diverge du corpus, quelqu'un a ajouté ou
                # retiré des données sans mettre le dénominateur à jour.
                if declare is None:
                    errors.append(f"dénominateur — {ss['code']} : référentiel déclaré mais "
                                  f"'couvert_referentiel_eur' absent (corpus présent : {present:.2f})")
                elif abs(present - declare) > max(1.0, abs(declare) * 0.005):
                    errors.append(f"dénominateur — {ss['code']} : couverture déclarée {declare:.2f} € "
                                  f"mais corpus réellement présent {present:.2f} € "
                                  f"(écart {present - declare:+.2f} €). Mettre à jour "
                                  f"'couvert_referentiel_eur' à {present:.2f}.")
            comptes = c * ss["poids_eur"]
            numerateur += comptes
            if ss.get("raccord_publie"):
                raccorde += comptes
            dist = euros_bloc.get(ss["code"], {})
            somme = sum(dist.values())
            if comptes > 0 and somme > 0:
                for n, e in dist.items():
                    part = comptes * e / somme
                    histo_univers[n] += part
                    histo_couvert[n] += part
            else:
                histo_univers["P0"] += comptes
                histo_couvert["P0"] += comptes
            # ADR-0007 — filet de dernier recours, indépendant de tout paramétrage : un bloc
            # ne peut pas être couvert au-delà de son poids. Contrairement au contrôle sur `c`,
            # celui-ci attrape aussi les cas où le poids lui-même a été déplacé entre
            # sous-segments. Un euro d'univers négatif est physiquement impossible.
            if comptes > ss["poids_eur"] * 1.005:
                errors.append(f"dénominateur — {ss['code']} : {comptes:.2f} € comptés pour un poids "
                              f"de {ss['poids_eur']:.2f} € — un bloc ne peut pas être couvert "
                              f"au-delà de lui-même (ADR-0007).")
            histo_univers["P0"] += ss["poids_eur"] - comptes   # non couvert = P0
            blocs.append({
                "code": ss["code"], "label": ss["label"],
                "poids_eur": ss["poids_eur"], "coefficient": round(c, 6),
                "corpus_present_eur": round(present, 2) if present is not None else None,
                "compte_eur": round(comptes, 2),
                "referentiel": ref["nom"] if ref else None,
                "raccord_publie": ss.get("raccord_publie", False),
                "ecart_millesime": ss.get("ecart_millesime", False),
                "sens_du_biais": ss.get("sens_du_biais"),
                "manque": ss.get("manque"),
            })

    total_couvert = sum(histo_couvert.values())
    P = (sum(NIVEAUX_P.index(n) * e for n, e in histo_couvert.items()) / total_couvert) if total_couvert else 0.0
    return {
        "methode": METHODE_CP,
        "volet": volet,
        "millesime_univers": denom["millesime"],
        "statut_revision_univers": denom["statut_revision"],
        "univers_eur": univers,
        "univers_consolide_publie_eur": denom["total_consolide_publie_eur"],
        "couvert_eur": round(numerateur, 2),
        "C": round(numerateur / univers, 6),
        "P": round(P, 3),
        "part_raccordee": round(raccorde / numerateur, 6) if numerateur else 0.0,
        "histogramme_univers": {n: round(v, 2) for n, v in histo_univers.items()},
        "histogramme_couvert": {n: round(v, 2) for n, v in histo_couvert.items()},
        "blocs": blocs,
    }


def couverture(node):
    """Répartition du montant racine par statut / millésime / profondeur du porteur (cf. METHODE_COUVERTURE)."""
    acc = {"statuts": {"confirme": 0.0, "estime": 0.0, "inconnu": 0.0},
           "annees": {}, "profondeurs": {}, "maj_renseignee": 0.0}

    def poser(n, euros, prof):
        if euros <= 0:
            return
        acc["statuts"][n["statut"]] += euros
        a = str(n.get("annee") or "?")
        acc["annees"][a] = acc["annees"].get(a, 0.0) + euros
        acc["profondeurs"][str(prof)] = acc["profondeurs"].get(str(prof), 0.0) + euros
        if n.get("source", {}).get("maj"):
            acc["maj_renseignee"] += euros

    def repartir(n, alloue, prof):
        kids = [c for c in n["enfants"] if isinstance(c.get("montant"), (int, float)) and c["montant"] > 0]
        total = sum(c["montant"] for c in kids)
        if not kids or alloue <= 0:
            poser(n, alloue, prof)
            return
        if total >= alloue:  # dépassement (transferts internes) : pro-rata
            for c in kids:
                repartir(c, alloue * c["montant"] / total, prof + 1)
        else:                # ventilation partielle : le reliquat reste au parent
            for c in kids:
                repartir(c, c["montant"], prof + 1)
            poser(n, alloue - total, prof)

    repartir(node, node.get("montant") or 0, 0)
    noeuds, inconnues, demandes = {"confirme": 0, "estime": 0, "inconnu": 0}, 0, 0

    def compter(n):
        nonlocal inconnues, demandes
        noeuds[n["statut"]] += 1
        if n["statut"] == "inconnu":
            inconnues += 1
            if (n.get("inconnu") or {}).get("url"):
                demandes += 1
        for c in n["enfants"]:
            compter(c)

    compter(node)
    m = node.get("montant") or 0
    return {
        "label": node["label"], "montant": m,
        "statuts": {k: round(v, 2) for k, v in acc["statuts"].items()},
        "pct_confirme": round(acc["statuts"]["confirme"] / m * 100, 1) if m else None,
        "annees": {k: round(v, 2) for k, v in sorted(acc["annees"].items())},
        "profondeurs": {k: round(v, 2) for k, v in sorted(acc["profondeurs"].items())},
        "maj_renseignee_pct": round(acc["maj_renseignee"] / m * 100, 1) if m else None,
        "noeuds": noeuds,
        "inconnues": {"total": inconnues, "avec_demande": demandes},
    }


def maj_readme(cov):
    """Régénère le tableau de couverture du README entre ses balises (si présentes)."""
    debut, fin = "<!-- couverture:debut -->", "<!-- couverture:fin -->"
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as fh:
        texte = fh.read()
    if debut not in texte or fin not in texte:
        return False
    md = lambda v: f"{v / 1e9:,.1f}".replace(",", " ").replace(".", ",") + " Md€"
    lignes = ["| Périmètre | Montant | ✅ confirmé (en €) | 🟡 estimé | ❓ à réclamer |", "|---|---|---|---|---|"]
    for cle, c in cov.items():
        s, m = c["statuts"], c["montant"]
        if not m:
            continue  # vues transverses (montant racine null) : hors tableau de couverture
        pc = lambda v: f"{v / m * 100:,.1f}".replace(".", ",") + " %" if m else "—"
        lignes.append(f"| {c['label']} | {md(m)} | **{pc(s['confirme'])}** | {pc(s['estime'])} | "
                      f"{c['inconnues']['total']} nœud(s), dont {c['inconnues']['avec_demande']} réclamé(s) |")
    lignes.append("")
    lignes.append("*Un euro est « confirmé » si le nœud le plus profond qui le porte l'est — la méthode complète "
                  "est dans [`site/couverture.json`](site/couverture.json). Les périmètres ne s'additionnent pas "
                  "(transferts entre administrations). Tableau régénéré par `build.py`.*")
    bloc = debut + "\n" + "\n".join(lignes) + "\n" + fin
    nouveau = texte[: texte.index(debut)] + bloc + texte[texte.index(fin) + len(fin):]
    if nouveau != texte:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(nouveau)
    return True


def valider_flux(doc, path, seen_ids):
    """Valide un fichier de flux (ADR-0001) : pôles déclarés, extrémités connues,
    montants sourcés comme des nœuds, noeuds_lies existants dans les arbres."""
    poles = doc.get("poles") or {}
    for f in doc.get("flux", []):
        fid = f.get("id", "?")
        for req in ("id", "de", "vers", "label", "montant", "annee", "statut", "source"):
            if req not in f:
                errors.append(f"{path}: flux — champ requis manquant '{req}' ({fid})")
        if f.get("de") not in poles or f.get("vers") not in poles:
            errors.append(f"{path}: flux — pôle non déclaré ({fid}: {f.get('de')} → {f.get('vers')})")
        if f.get("statut") not in STATUTS:
            errors.append(f"{path}: flux — statut invalide ({fid})")
        src = f.get("source") or {}
        for req in ("nom", "url", "producteur", "consulte_le"):
            if not src.get(req):
                errors.append(f"{path}: flux — source.{req} manquant ({fid})")
        for nid in f.get("noeuds_lies", []):
            if nid not in seen_ids:
                errors.append(f"{path}: flux — noeud_lie inexistant « {nid} » ({fid})")


# Au-delà de ce facteur, aucun effet de millésime n'explique plus l'écart : c'est
# une erreur d'imputation. Mesuré sur le corpus au 21/07/2026, un seul programme
# dépasse son montant — le 350 « JO et paralympiques 2024 », à ×1,44, parce que
# les versements tracés sont d'exécution 2023 face à un arbre en PLF 2025. Un
# écart de cette nature est légitime et déclaré ; un facteur 3 ne l'est pas.
SUR_RATTACHEMENT_FATAL = 3.0


def valider_sur_rattachement(arbres):
    """Pendant, sur l'axe P, de l'assertion `couvert_referentiel_eur` qui protège C.

    Une ligne payeuse ne peut pas verser plus qu'elle ne porte. Sans ce contrôle,
    rien n'empêchait de pointer 100 Md€ de bénéficiaires sur un programme qui en
    porte 2,9 : le build passait en silence et P gagnait 0,16 point (vérifié par
    exécution le 21/07/2026). Le plafond de `collecter_p5()` ne s'y oppose pas —
    il porte sur le BLOC entier, consommé à moins de 1 %."""
    montants, recu = {}, {}
    for racine in arbres:
        def idx(n):
            montants[n["id"]] = n.get("montant")
            for c in n.get("enfants", []):
                idx(c)
        idx(racine)
    for racine in arbres:
        def collecte(n):
            cible = n.get("rattachement_id")
            # mêmes conditions que collecter_p5() : sans elles, l'euro ne bouge pas
            if cible and n.get("identifiant") and isinstance(n.get("montant"), (int, float)):
                recu[cible] = recu.get(cible, 0.0) + n["montant"]
            for c in n.get("enfants", []):
                collecte(c)
        collecte(racine)
    for cible, somme in sorted(recu.items()):
        porte = montants.get(cible)
        if not porte or porte <= 0:
            continue
        ratio = somme / porte
        if ratio > SUR_RATTACHEMENT_FATAL:
            errors.append(f"sur-rattachement — « {cible} » reçoit {somme:,.2f} € de bénéficiaires "
                          f"rattachés pour une ligne qui en porte {porte:,.2f} € (×{ratio:.2f}). "
                          f"Au-delà de ×{SUR_RATTACHEMENT_FATAL:g}, aucun écart de millésime "
                          f"n'explique cela : c'est une erreur d'imputation (ADR-0006).")
        elif ratio > 1.0:
            warnings.append(f"sur-rattachement — « {cible} » reçoit {somme:,.2f} € pour une ligne "
                            f"qui en porte {porte:,.2f} € (×{ratio:.2f}) — écart de millésime "
                            f"probable, à vérifier.")


STATUTS_PLAFOND = {"ferme-droit", "communicable-sur-demande", "inexistant"}
# Le statut dérive l'effet du bouton, et on vérifie que le fichier ne ment pas :
# une donnée fermée ou inexistante éteint le bouton « réclamer », une donnée
# communicable le laisse (ADR-0006 §5).
EFFET_ATTENDU = {"ferme-droit": "reclamer-eteint", "inexistant": "reclamer-eteint",
                 "communicable-sur-demande": "reclamer-autorise"}


def valider_plafond(doc, blocs_connus):
    """Registre du plafond légal (ADR-0006 §5). Ce n'est NI un arbre NI un
    dénominateur : il n'entre dans aucun quotient — vérifié par le fait qu'il est
    chargé après indice_cp(). On contrôle ici que chaque entrée est citée à un
    article Légifrance non abrogé, et qu'une fermeture ne s'auto-déclare pas sans
    fondement — c'est le fichier le plus sensible du dépôt."""
    if doc is None:
        return
    for champ in ("millesime", "consulte_le", "principe", "entrees"):
        if champ not in doc:
            errors.append(f"plafond-legal — champ requis manquant '{champ}'")
            return
    vus = set()
    for e in doc["entrees"]:
        ident = e.get("id", "?")
        if ident in vus:
            errors.append(f"plafond-legal — id dupliqué « {ident} »")
        vus.add(ident)
        if e.get("statut") not in STATUTS_PLAFOND:
            errors.append(f"plafond-legal — {ident} : statut invalide « {e.get('statut')} »")
        if e.get("effet_bouton") != EFFET_ATTENDU.get(e.get("statut")):
            errors.append(f"plafond-legal — {ident} : effet_bouton « {e.get('effet_bouton')} » "
                          f"incohérent avec le statut « {e.get('statut')} » "
                          f"(attendu « {EFFET_ATTENDU.get(e.get('statut'))} »)")
        fonds = e.get("fondements") or []
        if not fonds:
            errors.append(f"plafond-legal — {ident} : aucune citation d'article — interdit, "
                          f"une fermeture ou une ouverture s'appuie toujours sur un texte")
        for fo in fonds:
            for c in ("reference", "url", "citation", "en_vigueur_depuis"):
                if not fo.get(c):
                    errors.append(f"plafond-legal — {ident} : fondement sans '{c}'")
            if not str(fo.get("url", "")).startswith("https://www.legifrance.gouv.fr/"):
                errors.append(f"plafond-legal — {ident} : l'URL d'un fondement doit pointer sur "
                              f"Légifrance (l'article lui-même) — « {fo.get('url')} »")
            if fo.get("abroge") is True:
                errors.append(f"plafond-legal — {ident} : fondement sur un article abrogé "
                              f"« {fo.get('reference')} » — la ligne ne tient plus")
        # La portée, si elle vise des blocs, doit désigner des blocs réels.
        portee = e.get("portee") or {}
        if portee.get("type") == "bloc_univers":
            for v in portee.get("valeurs", []):
                if v not in blocs_connus:
                    errors.append(f"plafond-legal — {ident} : portée sur un bloc inconnu « {v} »")


def valider_rattachements(node, path, seen_ids):
    """Un bénéficiaire ne peut atteindre P5 (ADR-0006) qu'avec les DEUX : un
    identifiant machine et un rattachement à une ligne payeuse réelle."""
    def walk(n):
        cible = n.get("rattachement_id")
        if cible is not None:
            if cible not in seen_ids:
                errors.append(f"{path}: rattachement_id inexistant « {cible} » ({n['id']})")
            elif cible == n["id"]:
                errors.append(f"{path}: rattachement_id pointe sur le nœud lui-même ({n['id']})")
        ident = n.get("identifiant")
        if ident is not None:
            if not isinstance(ident, dict) or not ident.get("type") or not ident.get("valeur"):
                errors.append(f"{path}: identifiant sans type ou sans valeur ({n['id']})")
            elif ident["type"] == "SIREN" and not str(ident["valeur"]).isdigit():
                errors.append(f"{path}: SIREN non numérique « {ident['valeur']} » ({n['id']})")
        for c in n.get("enfants", []):
            walk(c)
    walk(node)


def valider_denominateur(doc, path):
    """Dénominateur de l'indice C·P (ADR-0006) : ce n'est PAS un arbre de nœuds.
    On vérifie ici les seuls invariants qui rendraient l'indice faux ; le calcul
    de C et de P viendra avec l'étape 4 de l'issue #50."""
    for req in ("millesime", "volet", "statut_revision", "total_brut_eur",
                "total_consolide_publie_eur", "base_retenue", "source", "segments"):
        if req not in doc:
            errors.append(f"{path}: dénominateur — champ requis manquant '{req}'")
            return
    if doc["base_retenue"] != "brut":
        errors.append(f"{path}: dénominateur — l'ADR-0006 impose la base brute")
    total = 0
    for seg in doc["segments"]:
        somme = sum(ss["poids_eur"] for ss in seg["sous_segments"])
        # invariant cardinal : la somme des sous-segments doit refermer le segment,
        # sinon des euros d'univers disparaissent ou sont comptés deux fois.
        if abs(somme - seg["poids_brut_eur"]) > 2:
            errors.append(f"{path}: dénominateur — segment {seg['code']} : "
                          f"somme des sous-segments {somme} ≠ poids {seg['poids_brut_eur']}")
        total += seg["poids_brut_eur"]
        for ss in seg["sous_segments"]:
            ident = f"{path}: dénominateur — {ss['code']}"
            if ss.get("poids_derive") and not ss.get("methode_poids"):
                errors.append(f"{ident} : poids dérivé sans methode_poids")
            if ss.get("sens_du_biais") not in ("sous-estime", "sur-estime", "neutre"):
                errors.append(f"{ident} : sens_du_biais absent ou invalide")
            ref = ss.get("referentiel_comptage")
            if ref is None:
                # pas de référentiel homogène → aucune couverture ne peut être comptée
                if ss.get("couvert_referentiel_eur"):
                    errors.append(f"{ident} : couverture déclarée sans référentiel de comptage "
                                  f"— interdit par l'ADR-0006 (règle du référentiel homogène)")
            elif not ref.get("total_eur") or not ref.get("source", {}).get("url", "").startswith("https://"):
                errors.append(f"{ident} : référentiel de comptage sans total ou sans source HTTPS")
            else:
                # ADR-0007 — la comptabilité du référentiel doit être déclarée…
                base = ref.get("base_comptable")
                if base not in BASES_COMPTABLES:
                    errors.append(f"{ident} : référentiel sans 'base_comptable' valide "
                                  f"(attendu l'une de {sorted(BASES_COMPTABLES)}). Sans elle, "
                                  f"rien n'empêche de mesurer le coefficient dans une "
                                  f"comptabilité et de l'appliquer à une autre.")
                # …et elle ne peut pas être celle du poids, sans quoi c = 1 par construction.
                elif base == BASE_INTERDITE_EN_REFERENTIEL:
                    errors.append(f"{ident} : référentiel en base SEC — interdit. Le poids du "
                                  f"bloc est lui-même en SEC : le coefficient vaudrait 1 par "
                                  f"construction et ne mesurerait rien (ADR-0007).")
    if abs(total - doc["total_brut_eur"]) > 3:
        errors.append(f"{path}: dénominateur — somme des segments {total} ≠ total_brut_eur {doc['total_brut_eur']}")


def valider_racine_cp(node, path, codes):
    """Chaque fichier de données déclare ce qu'il représente dans l'univers
    (bloc_univers) et jusqu'où il suit l'euro (niveaux) — ADR-0006, étape 3."""
    if "bloc_univers" not in node:
        errors.append(f"{path}: racine sans 'bloc_univers' (mettre null si l'arbre ne compte pas dans la couverture)")
    else:
        bloc = node["bloc_univers"]
        if bloc is not None and bloc not in codes:
            errors.append(f"{path}: bloc_univers « {bloc} » inconnu du dénominateur")
    if "volet" not in node:
        errors.append(f"{path}: racine sans 'volet' (depenses / recettes / mixte, ou null si l'arbre ne compte pas)")
    elif node["volet"] not in (None, "depenses", "recettes", "mixte"):
        errors.append(f"{path}: volet « {node['volet']} » invalide")
    elif node.get("bloc_univers") and node["volet"] is None:
        errors.append(f"{path}: bloc_univers déclaré sans volet — le calcul ne saurait pas contre quel dénominateur mesurer")
    # ADR-0007 : un arbre qui compte dans un bloc dit dans quelle comptabilité il
    # est libellé. C'est ce qui permet de refuser mécaniquement un coefficient
    # mesuré entre deux comptabilités différentes.
    if node.get("bloc_univers"):
        base = node.get("base_comptable")
        if base not in BASES_COMPTABLES:
            errors.append(f"{path}: racine sans 'base_comptable' valide "
                          f"(attendu l'une de {sorted(BASES_COMPTABLES)})")
    niveaux = node.get("niveaux")
    if not isinstance(niveaux, list) or not niveaux:
        errors.append(f"{path}: racine sans table 'niveaux'")
        return
    for n in niveaux:
        if n is not None and n not in NIVEAUX_P:
            errors.append(f"{path}: niveau « {n} » hors de l'échelle P0→P6")
    if niveaux[0] is None:
        errors.append(f"{path}: le niveau de la racine ne peut pas être null")

    def prof_max(n, p=0):
        return max([prof_max(c, p + 1) for c in n.get("enfants", [])] or [p])
    pm = prof_max(node)
    if pm >= len(niveaux):
        errors.append(f"{path}: profondeur max {pm} non couverte par la table de {len(niveaux)} niveaux")


# ── Pages /perimetre et /methode (issue #50) ─────────────────────────────────
# Elles sont GÉNÉRÉES depuis site/couverture.json, jamais écrites à la main : une
# page rédigée dériverait au premier changement de C, et c'est exactement ce que
# ce projet ne peut pas se permettre. Tout chiffre affiché ici vient du calcul.

CSS_PAGE = """
:root{--primary:#2f4d8a; --ink:#161616; --mute:#666; --border:#ddd;
      --surface:#f6f6f6; --ok:#18753c; --ok-bg:#dffee6; --est:#b34000;
      --est-bg:#ffecc2; --unk:#ce0500; --unk-bg:#ffe9e9;}
*{box-sizing:border-box; margin:0; padding:0;}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
     color:var(--ink); background:#fff; line-height:1.55;}
a{color:var(--primary);} :focus-visible{outline:2px solid var(--primary); outline-offset:2px;}
header{padding:14px 20px; border-bottom:1px solid var(--border); display:flex;
       gap:14px; align-items:baseline; flex-wrap:wrap;}
header h1{font-size:1.15rem;} header a{font-size:.85rem;}
main{max-width:860px; margin:0 auto; padding:22px 20px 80px;}
h2{font-size:1.05rem; margin:30px 0 10px; padding-bottom:5px; border-bottom:2px solid var(--primary);}
h3{font-size:.95rem; margin:20px 0 6px;}
p,li{font-size:.9rem;} p{margin:8px 0;} ul{margin:8px 0 8px 20px;}
.chiffre{display:flex; gap:26px; flex-wrap:wrap; margin:14px 0;}
.chiffre div{background:var(--surface); border-radius:6px; padding:12px 16px; flex:1 1 190px;}
.chiffre b{display:block; font-size:1.5rem; color:var(--primary);}
.chiffre span{font-size:.75rem; color:var(--mute);}
table{border-collapse:collapse; width:100%; margin:12px 0; font-size:.82rem;}
th,td{border:1px solid var(--border); padding:6px 8px; text-align:left; vertical-align:top;}
th{background:var(--surface);} td.n{text-align:right; white-space:nowrap;}
.badge{display:inline-block; border-radius:4px; padding:1px 7px; font-size:.68rem;
       font-weight:700; text-transform:uppercase;}
.badge.ok{background:var(--ok-bg); color:var(--ok);}
.badge.unk{background:var(--unk-bg); color:var(--unk);}
.callout{border-left:4px solid var(--primary); background:var(--surface);
         padding:10px 14px; margin:14px 0; font-size:.85rem;}
.callout.alerte{border-left-color:var(--unk); background:var(--unk-bg);}
.manque{font-size:.78rem; color:var(--mute); margin-top:6px;}
.manque b{color:var(--ink);}
.manque details{margin:6px 0;}
.manque summary{cursor:pointer; color:var(--primary); font-weight:600;
                padding:3px 0; list-style-position:inside;}
.manque details[open] summary{margin-bottom:4px;}
.manque details p{font-size:.78rem; margin:0 0 7px; max-width:70ch;}
.manque .qui{margin-top:6px; padding-top:5px; border-top:1px dotted var(--border);
             word-break:break-word;}
.barre{display:flex; align-items:center; gap:8px; margin:3px 0; font-size:.78rem;}
.barre i{display:block; height:13px; background:var(--primary); border-radius:2px;}
.barre span:first-child{width:2.2em; font-weight:700; font-style:normal;}
@media(max-width:768px){
  main{padding:16px 14px 60px;} .chiffre{gap:12px;}
  /* Un tableau à 4 colonnes est illisible à 375 px, et le faire défiler
     horizontalement l'est autant. Chaque ligne devient donc un bloc empilé,
     chaque cellule portant son intitulé via data-col. */
  table,tbody,tr,td{display:block; width:100%;}
  thead{display:none;}
  tr{border:1px solid var(--border); border-radius:6px; margin:0 0 10px; padding:8px 10px;}
  td{border:none; padding:3px 0; font-size:.82rem;}
  td.n{text-align:left;}
  td[data-col]:before{content:attr(data-col) " : "; color:var(--mute); font-size:.72rem;}
  td[data-col="Bloc"]:before{content:none;}
}
"""

def _md(x):
    return f"{x/1e9:,.1f}".replace(",", " ").replace(".", ",")

def _fr(x, dec=1):
    """Décimale française : le site est francophone, un « 46.0 % » y détonne."""
    return f"{x:.{dec}f}".replace(".", ",")


def _paragraphes(txt, cible=340):
    """Les champs `manque.quoi` sont des pavés d'un seul tenant de plusieurs
    milliers de signes. Les déplier tels quels ne les rendrait pas lisibles :
    on les coupe sur des frontières de PHRASE, en groupant jusqu'à ~`cible`
    signes. Découper au caractère trancherait au milieu d'un mot ou d'un nombre."""
    morceaux = txt.split(". ")
    phrases, courante = [], ""
    for i, morceau in enumerate(morceaux):
        # Le séparateur n'est réinjecté qu'ENTRE les fragments : le dernier porte
        # déjà sa ponctuation, et la lui rajouter doublait le point final.
        courante += morceau + (". " if i < len(morceaux) - 1 else "")
        if len(courante) >= cible:
            phrases.append(courante.strip()); courante = ""
    if courante.strip():
        phrases.append(courante.strip())
    return "".join(f"<p>{p}</p>" for p in phrases) or f"<p>{txt}</p>"

def _page(titre, corps, sous_titre=""):
    return (f'<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="UTF-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'<title>{html.escape(titre)} — Où va l\'argent public ?</title>\n'
            f'<style>{CSS_PAGE}</style>\n</head>\n<body>\n'
            f'<header><h1>{html.escape(titre)}</h1>'
            f'<a href="index.html">← Où va l\'argent public ?</a></header>\n'
            f'<main>\n{sous_titre}{corps}\n</main>\n'
            f'<!-- Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN -->\n'
            f'</body>\n</html>\n')

def _histo(h):
    total = sum(h.values()) or 1
    out = []
    for n in NIVEAUX_P:
        part = h.get(n, 0.0) / total
        out.append(f'<div class="barre"><span>{n}</span>'
                   f'<i style="width:{max(part*100,0):.1f}%"></i>'
                   f'<span>{_fr(part*100)} %</span></div>')
    return "".join(out)

def generer_page_plafond(plafond):
    """Écrit site/plafond.html depuis data/plafond-legal.json (ADR-0006 §5)."""
    if plafond is None:
        return
    p = ['<div class="callout"><b>La communication est la règle, le secret l\'exception.</b><br>'
         + html.escape(plafond["principe"]) + "</div>"]
    fermes = [e for e in plafond["entrees"] if e["statut"] == "ferme-droit"]
    fermes_actifs = [e for e in fermes if (e.get("portee") or {}).get("type") != "aucune"]
    p.append("<h2>Ce que le droit ferme absolument</h2>")
    if fermes and not fermes_actifs:
        p.append('<div class="callout"><b>Aucune donnée de l\'arbre aujourd\'hui.</b> Le droit connaît '
                 "des secrets absolus — un document couvert par le secret de la défense nationale, ou une "
                 "donnée nominative de personne physique, n'est communicable à personne. Mais l'arbre ne "
                 "contient à ce jour que des personnes morales et des agrégats budgétaires : aucun de ces "
                 "secrets n'y trouve à s'appliquer. Les deux entrées ci-dessous sont documentées comme "
                 "<b>frontières</b> — elles deviendront actives si l'arbre s'approche d'une pièce classifiée "
                 "ou d'une donnée individuelle.</div>")
        for e in fermes:
            p.append(_entree_plafond_html(e))
    elif not fermes:
        p.append('<div class="callout"><b>Rien, à ce jour.</b> Une revue article par article de cinq '
                 "fondements (droit d'accès, défense nationale, vie privée, secret des affaires et fiscal, "
                 "secret statistique), chacun soumis à double contradiction, n'a établi <b>aucune donnée de "
                 "l'arbre que le droit interdise de publier</b>. Les protections invoquées portent sur des "
                 "mentions occultables (CRPA art. L311-7) ou restreignent le cercle des destinataires — "
                 "elles ne ferment pas le montant.</div>")
    else:
        for e in fermes_actifs:
            p.append(_entree_plafond_html(e))
    p.append("<h2>Non publié d'office, mais obtenable sur demande</h2>")
    p.append("<p>Ces données ne sont pas fermées : elles ne sont simplement pas mises en ligne "
             "d'office. Toute personne peut les demander, et le bouton « réclamer » du site vous y aide.</p>")
    for e in plafond["entrees"]:
        if e["statut"] == "communicable-sur-demande":
            p.append(_entree_plafond_html(e))
    p.append(f'<p class="manque">Revue juridique {plafond["millesime"]}, articles vérifiés au texte sur '
             f'Légifrance le {plafond["consulte_le"]}. Registre brut : '
             '<a href="https://github.com/MrPognon/MonPognon/blob/main/data/plafond-legal.json">'
             "data/plafond-legal.json</a>.</p>")
    with open(os.path.join(ROOT, "site", "plafond.html"), "w", encoding="utf-8") as fh:
        fh.write(_page("Le plafond légal", "\n".join(p),
                       "<p>Ce que le droit français ferme, ce qu'il oblige à publier, "
                       "et ce qui reste obtenable sur demande — cité article par article.</p>"))


def _entree_plafond_html(e):
    badge = {"ferme-droit": '<span class="badge unk">fermé par le droit</span>',
             "communicable-sur-demande": '<span class="badge ok">communicable sur demande</span>',
             "inexistant": '<span class="badge">donnée non produite</span>'}[e["statut"]]
    h = [f'<h3>{html.escape(e["quoi"].split(". ")[0])} {badge}</h3>']
    if len(e["quoi"].split(". ", 1)) > 1:
        h.append(f'<p>{html.escape(e["quoi"].split(". ", 1)[1])}</p>')
    if e.get("note"):
        h.append(f'<div class="callout">{html.escape(e["note"])}</div>')
    h.append("<table><tbody>")
    for fo in e["fondements"]:
        h.append(f'<tr><td><b>{html.escape(fo["reference"])}</b><br>'
                 f'<a href="{html.escape(fo["url"])}">texte sur Légifrance</a>, '
                 f'en vigueur depuis le {fo["en_vigueur_depuis"]}</td>'
                 f'<td>« {html.escape(fo["citation"])} »</td></tr>')
    h.append("</tbody></table>")
    return "".join(h)


def generer_pages(cov_doc, plafond=None):
    """Écrit site/perimetre.html et site/methode.html depuis le calcul C·P."""
    cps = cov_doc["cp"]

    # ── /perimetre : l'univers, bloc par bloc, avec ce qui manque et qui contacter
    c = []
    for volet in ("depenses", "recettes"):
        cp = cps.get(volet)
        if not cp:
            continue
        lib = "Dépenses" if volet == "depenses" else "Recettes"
        c.append(f"<h2>{lib}</h2>")
        c.append('<div class="chiffre">'
                 f'<div><b>{_fr(cp["C"]*100)} %</b><span>des euros de l\'univers sont dans l\'arbre</span></div>'
                 f'<div><b>{_fr(cp["P"], 2)} / 6</b><span>profondeur atteinte (P0→P6)</span></div>'
                 f'<div><b>{_md(cp["couvert_eur"])} Md€</b><span>couverts sur {_md(cp["univers_eur"])} Md€</span></div>'
                 '</div>')
        c.append('<p><b>Ce pourcentage mesure le périmètre, pas la finesse.</b> Les deux nombres '
                 'ne se moyennent jamais — voir <a href="methode.html">la méthode</a>.</p>')
        c.append("<h3>Où en est chaque bloc</h3>")
        c.append("<table><thead><tr><th>Bloc</th><th>Poids</th><th>Couvert</th>"
                 "<th>Référentiel de comptage</th></tr></thead><tbody>")
        for b in cp["blocs"]:
            pct = b["coefficient"] * 100
            bdg = (f'<span class="badge ok">{_fr(pct, 0)} %</span>' if b["coefficient"] > 0
                   else '<span class="badge unk">compte zéro</span>')
            ref = html.escape(b["referentiel"]) if b.get("referentiel") else "<i>aucun</i>"
            ligne = (f'<tr><td data-col="Bloc"><b>{html.escape(b["label"])}</b>')
            if not b["coefficient"] and b.get("manque"):
                m = b["manque"]
                quoi = html.escape(m.get("quoi", ""))
                # Accroche = la première phrase, qui porte toujours le motif du
                # blocage (« RACCORD MANQUANT, ET NON DONNÉE MANQUANTE. »…).
                # Le reste est déplié à la demande plutôt que TRONQUÉ : couper
                # laissait le lecteur sans la carte, et sans moyen de la voir.
                # La POSITION de coupe est calculée à part de la chaîne affichée :
                # l'ellipse ajoutée à l'accroche ne doit pas décaler le reste, sous
                # peine de manger un caractère et de repartir au milieu d'un mot.
                coupe = quoi.find(". ")
                if 0 < coupe < 260:
                    fin, accroche = coupe + 1, quoi[:coupe + 1]
                else:
                    fin = len(quoi[:220].rsplit(" ", 1)[0])
                    accroche = quoi[:fin] + "…"
                reste = quoi[fin:].strip()
                # Le contact vit DANS le dépliant : replié, il poussait le poids et le
                # taux de couverture sous la ligne de flottaison en vue mobile, alors que
                # ce sont les deux chiffres qu'on vient chercher en premier.
                contact = ""
                if m.get("contact"):
                    contact = f'<div class="qui"><b>Qui contacter :</b> {html.escape(m["contact"])}'
                    if m.get("url"):
                        u = html.escape(m["url"])
                        contact += f'<br><a href="{u}">{u}</a>'
                    contact += "</div>"
                ligne += f'<div class="manque"><b>{accroche}</b>'
                if reste or contact:
                    ligne += (f'<details><summary>Ce qui a été cherché, pourquoi cela ne convient '
                              f'pas, et qui contacter ({len(reste)} signes)</summary>'
                              f'{_paragraphes(reste) if reste else ""}{contact}</details>')
                ligne += "</div>"
            ligne += (f'</td><td class="n" data-col="Poids">{_md(b["poids_eur"])} Md€</td>'
                      f'<td class="n" data-col="Couvert">{bdg}</td>'
                      f'<td data-col="Référentiel">{ref}</td></tr>')
            c.append(ligne)
        c.append("</tbody></table>")
        c.append("<h3>Profondeur des euros couverts</h3>")
        c.append(_histo(cp["histogramme_couvert"]))
        zero = [b for b in cp["blocs"] if not b["coefficient"]]
        if zero:
            somme = sum(b["poids_eur"] for b in zero)
            c.append(f'<div class="callout alerte"><b>{_md(somme)} Md€ comptent zéro.</b> '
                     f'{len(zero)} blocs sur {len(cp["blocs"])} n\'ont aucun référentiel de comptage '
                     'homogène : leur couverture ne peut pas être mesurée sans diviser un euro d\'une '
                     'comptabilité par un euro d\'une autre. Le détail de chaque blocage est dans le '
                     'tableau ci-dessus, et la règle dans <a href="methode.html">la méthode</a>.</div>')
        c.append(f'<p class="manque">Univers : comptes nationaux INSEE, millésime {cp["millesime_univers"]} '
                 f'({html.escape(cp["statut_revision_univers"])}), base brute {_md(cp["univers_eur"])} Md€ '
                 f'— le total consolidé publié ({_md(cp["univers_consolide_publie_eur"])} Md€) est rappelé '
                 'ici mais n\'est pas le dénominateur retenu.</p>')

    c.append("<h2>Ce que ce compteur ne compte pas</h2>")
    c.append('<div class="callout"><p>Le périmètre des administrations publiques (S13) <b>exclut</b> :</p>'
             "<ul><li>les <b>entreprises publiques marchandes</b> ;</li>"
             "<li>les <b>stocks de dette</b> et les engagements hors bilan ;</li>"
             "<li>les <b>dépenses fiscales</b> (exonérations, crédits d'impôt).</li></ul>"
             "<p><b>Un compteur à 100 % ne réaliserait donc pas l'ambition « tous les euros ».</b> "
             "Cette note est permanente.</p></div>")

    with open(os.path.join(ROOT, "site", "perimetre.html"), "w", encoding="utf-8") as fh:
        fh.write(_page("Le périmètre", "\n".join(c),
                       "<p>Ce que le site couvre, ce qu'il ne couvre pas, et pourquoi — "
                       "bloc par bloc, avec qui contacter pour obtenir ce qui manque.</p>"))

    # ── /methode : comment l'indice est calculé, et ce qu'il ne mesure pas
    m = []
    m.append("<h2>Deux nombres, jamais moyennés</h2>")
    m.append("<p><b>C — couverture de périmètre.</b> Part des euros de l'univers des administrations "
             "publiques représentés dans l'arbre.<br>"
             "<b>P — profondeur.</b> Jusqu'où on suit l'euro, sur une échelle de destination, "
             "<b>calculée sur les seuls euros couverts</b>.</p>")
    m.append("<p>Les réduire à une moyenne écraserait celle qui compte le plus. Aucun fichier généré "
             "ne contient de score global.</p>")
    m.append("<h2>L'échelle de profondeur</h2>")
    m.append("<table><thead><tr><th>Niveau</th><th>Ce qu'on voit</th></tr></thead><tbody>" + "".join(
        f"<tr><td><b>{n}</b></td><td>{d}</td></tr>" for n, d in [
            ("P0", "agrégat ou sous-secteur non ventilé"),
            ("P1", "politique publique (mission, branche, strate)"),
            ("P2", "programme, poste comptable, ou entité administrative nommée"),
            ("P3", "action et sous-action — la ligne budgétaire fine"),
            ("P4", "organisme destinataire identifié"),
            ("P5", "<b>bénéficiaire final nommé</b>, avec identifiant, rattaché à sa ligne payeuse"),
            ("P6", "<b>pièce justificative</b> référencée"),
        ]) + "</tbody></table>")
    m.append("<p>Un cran qui décrit <b>comment</b> l'argent est dépensé (titre budgétaire, nature de "
             "dépense) et non <b>à qui</b> il va n'avance pas P.</p>")
    m.append("<h2>La règle du référentiel homogène</h2>")
    m.append('<div class="callout"><b>On ne divise jamais un euro d\'une comptabilité par un euro '
             "d'une autre.</b> Le taux de couverture d'un bloc est mesuré à l'intérieur d'un "
             "référentiel homogène (budget de l'État ÷ budget de l'État, comptes locaux ÷ comptes "
             "locaux), puis appliqué au poids en comptabilité nationale.</div>")
    m.append("<p>Conséquence assumée : <b>un bloc sans référentiel homogène compte zéro</b>, même "
             "lorsque le site le documente intégralement. Les comptes de la Sécurité sociale sont "
             "dans l'arbre, sourcés et confirmés — et ils comptent zéro, faute de raccord publié "
             'entre leur comptabilité et la comptabilité nationale. Voir <a href="perimetre.html">le '
             "périmètre</a> pour le détail de chaque blocage.</p>")
    m.append("<h2>Ce que le compteur ne mesure pas</h2>")
    m.append("<ul><li><b>L'exactitude des montants.</b> C mesure la largeur, P la finesse. La qualité "
             "du sourçage est un indicateur distinct, affiché à part.</li>"
             "<li><b>Ce qui est fermé par le droit</b> (vie privée, secret des affaires, secret de la "
             "défense) est documenté mais <b>n'entre dans aucun quotient</b> : le retirer du "
             "dénominateur reviendrait à se donner une bonne note en rétrécissant l'épreuve. "
             "Le détail article par article est sur <a href=\"plafond.html\">la page du plafond "
             "légal</a> — à ce jour, aucune donnée de l'arbre n'est fermée par le droit ; deux secrets absolus (défense, données nominatives) y sont documentés comme frontières.</li></ul>")
    m.append("<h2>Contre la triche</h2>")
    m.append("<p>La règle ci-dessus est vérifiée par le programme qui construit le site : chaque "
             "référentiel et chaque arbre déclarent leur comptabilité, et une divergence fait échouer "
             "la publication.</p>")
    m.append('<div class="callout"><b>Sa limite, énoncée plutôt que promise.</b> Ce contrôle compare '
             "des <b>étiquettes et des montants déclarés</b> ; il ne relit pas les sources. Un "
             "référentiel étiqueté d'une comptabilité mais issu d'une autre passerait, comme "
             "passerait un montant fabriqué mais plausible. Le contrôle rend ces erreurs visibles "
             "dans l'historique public des modifications — il ne les rend pas impossibles. "
             "<b>La relecture humaine reste nécessaire.</b></div>")
    m.append('<p class="manque">Méthode complète et décisions d\'architecture : '
             '<a href="https://github.com/MrPognon/MonPognon/tree/main/docs/adr">docs/adr</a> '
             "(ADR-0006 pour l'indice, ADR-0007 pour le contrôle). Le calcul lui-même est dans "
             '<a href="https://github.com/MrPognon/MonPognon/blob/main/scripts/build.py">scripts/build.py</a>, '
             'et ses résultats bruts dans <a href="couverture.json">couverture.json</a>.</p>')

    with open(os.path.join(ROOT, "site", "methode.html"), "w", encoding="utf-8") as fh:
        fh.write(_page("La méthode", "\n".join(m),
                       "<p>Comment la complétion de ce site est mesurée — et ce que "
                       "cette mesure ne dit pas.</p>"))
    generer_page_plafond(plafond)


def main():
    data, fiches, seen = {}, {}, set()
    flux_docs, denominateurs = {}, {}
    # Fiches de collectivités (ADR-0004), tous échelons : communes, départements,
    # régions, syndicats. Elles sont validées comme le reste mais publiées en
    # fragments individuels — jamais dans data.js, qui resterait sinon inchargeable.
    ECHELONS_FICHES = ("communes", "groupements", "departements", "regions",
                       "syndicats", "ccas", "sdis")
    fiches_dirs = {os.path.join(ROOT, "data", "collectivites", e) + os.sep: e
                   for e in ECHELONS_FICHES}
    # Les bénéficiaires de subventions empruntent le même chemin que les fiches
    # (ADR-0004) : publiés en fragments, JAMAIS inlinés dans data.js — 112 722
    # nœuds y ajouteraient ~31 Mo — mais présents dans `arbres`, donc comptés
    # par indice_cp(), qui lit les arbres en mémoire et non le fichier publié.
    fiches_dirs[os.path.join(ROOT, "data", "etat", "subventions") + os.sep] = "subventions"
    flux_dir = os.path.join(ROOT, "data", "flux") + os.sep
    denom_dir = os.path.join(ROOT, "data", "denominateurs") + os.sep
    plafond_path = os.path.join(ROOT, "data", "plafond-legal.json")
    plafond = None
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True)):
        key = os.path.relpath(f, os.path.join(ROOT, "data")).replace(os.sep, "_").removesuffix(".json")
        with open(f, encoding="utf-8") as fh:
            node = json.load(fh)
        if f.startswith(denom_dir):         # dénominateurs C·P (ADR-0006) : pas des arbres
            valider_denominateur(node, os.path.relpath(f, ROOT))
            denominateurs[node.get("volet", "?")] = node
            continue
        if f == plafond_path:               # plafond légal (ADR-0006 §5) : contexte juridique,
            plafond = node                  # jamais un arbre, jamais dans un quotient. Validé plus bas.
            continue
        if f.startswith(flux_dir):          # flux (ADR-0001) : validés après les arbres
            flux_docs[os.path.relpath(f, ROOT)] = node
            continue
        resoudre_sources(node, os.path.relpath(f, ROOT))
        validate(node, os.path.relpath(f, ROOT), seen)
        ech = next((e for d, e in fiches_dirs.items() if f.startswith(d)), None)
        if ech:
            # clé = (échelon, code) : un département « 45 » et une commune « 45001 »
            # ne peuvent pas se marcher dessus, et l'échelon suit jusqu'au fragment.
            fiches[(ech, os.path.basename(f).removesuffix(".json"))] = node
        else:
            data[key] = node
    for path, doc in flux_docs.items():
        valider_flux(doc, path, seen)
    # Qualification C·P : validée APRÈS la boucle, le dénominateur devant être chargé
    codes = {ss["code"] for d in denominateurs.values()
             for seg in d["segments"] for ss in seg["sous_segments"]}
    for cle, node in list(data.items()) + [(f"{e}/{c}", n) for (e, c), n in fiches.items()]:
        valider_racine_cp(node, cle, codes)
        valider_rattachements(node, cle, seen)
    if "--show" in sys.argv:  # affiche un nœud avec sa source résolue (ADR-0005)
        cible = sys.argv[sys.argv.index("--show") + 1]
        def chercher(n):
            if n["id"] == cible: return n
            return next((r for c in n.get("enfants", []) if (r := chercher(c))), None)
        for arbre in list(data.values()) + list(fiches.values()):
            n = chercher(arbre)
            if n:
                apercu = {k: v for k, v in n.items() if k != "enfants"}
                apercu["enfants"] = f"[{len(n.get('enfants', []))} enfant(s)]"
                print(json.dumps(apercu, ensure_ascii=False, indent=1)); return
        print(f"id introuvable : {cible}", file=sys.stderr); sys.exit(1)
    # Indice C·P (ADR-0006) : calculé AVANT le verdict, et donc AUSSI en --check.
    # Il était auparavant produit dans la seule branche de génération : la CI ne
    # l'exerçait jamais, et un dénominateur périmé passait inaperçu.
    cov = {k: couverture(n) for k, n in data.items()}
    cov_doc = {"methode": METHODE_COUVERTURE, "arbres": cov}
    arbres = list(data.values()) + list(fiches.values())
    valider_bases_comptables(arbres, denominateurs)   # ADR-0007, AVANT le calcul
    valider_sur_rattachement(arbres)                 # pendant de la règle sur l'axe P
    cov_doc["cp"] = {v: indice_cp(arbres, d) for v, d in sorted(denominateurs.items())}
    # Plafond légal validé APRÈS le calcul C·P, et jamais passé à indice_cp() :
    # la preuve mécanique qu'il « n'entre dans aucun quotient » (ADR-0006 §5).
    valider_plafond(plafond, codes)

    for w in warnings: print("AVERTISSEMENT:", w)
    if errors:
        for e in errors: print("ERREUR:", e, file=sys.stderr)
        sys.exit(1)
    if fiches:
        par_ech = {}
        for (e, _), _n in fiches.items():
            par_ech[e] = par_ech.get(e, 0) + 1
        extra = " + " + " + ".join(f"{v} {k}" for k, v in sorted(par_ech.items()))
    else:
        extra = ""
    n_flux = sum(len(d.get("flux", [])) for d in flux_docs.values())
    if n_flux:
        extra += f" + {n_flux} flux"
    print(f"OK — {len(data)} fichiers{extra}, {len(seen)} nœuds validés")
    if "--check" not in sys.argv:
        out = os.path.join(ROOT, "site", "data.js")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/)\n")
            fh.write("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
        print("→", out)
        if fiches:
            for ech in {e for e, _ in fiches}:
                os.makedirs(os.path.join(ROOT, "site", "data", ech), exist_ok=True)
            for (ech, code), node in sorted(fiches.items()):
                with open(os.path.join(ROOT, "site", "data", ech, code + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(node, fh, ensure_ascii=False)
            print(f"→ site/data/<échelon>/ ({len(fiches)} fragment(s))")
            with open(os.path.join(ROOT, "site", "communes-index.js"), "w", encoding="utf-8") as fh:
                fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/)\n")
                # « e » = échelon : le site sait ainsi où chercher le fragment et
                # comment libeller le résultat (commune, département, région, syndicat).
                idx = [{"i": code, "e": ech, "n": n["label"].split(" (")[0]}
                       for (ech, code), n in sorted(fiches.items())]
                fh.write("window.COMMUNES_IDX = " + json.dumps(idx, ensure_ascii=False) + ";\n")
        # cov_doc est calculé plus haut (avant le verdict) : la CI l'exerce aussi.
        with open(os.path.join(ROOT, "site", "couverture.json"), "w", encoding="utf-8") as fh:
            json.dump(cov_doc, fh, ensure_ascii=False, indent=1)
        with open(os.path.join(ROOT, "site", "couverture.js"), "w", encoding="utf-8") as fh:
            fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/)\n")
            fh.write("window.COUVERTURE = " + json.dumps(cov_doc, ensure_ascii=False) + ";\n")
        if flux_docs:
            fusion = {"poles": {}, "flux": []}
            for d in flux_docs.values():
                fusion["poles"].update(d.get("poles", {}))
                fusion["flux"] += d.get("flux", [])
            with open(os.path.join(ROOT, "site", "flux.js"), "w", encoding="utf-8") as fh:
                fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/flux/)\n")
                fh.write("window.FLUX = " + json.dumps(fusion, ensure_ascii=False) + ";\n")
        if plafond is not None:              # plafond légal : publié pour gater le bouton « réclamer »
            with open(os.path.join(ROOT, "site", "plafond.js"), "w", encoding="utf-8") as fh:
                fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/plafond-legal.json)\n")
                fh.write("window.PLAFOND = " + json.dumps(plafond, ensure_ascii=False) + ";\n")
        generer_pages(cov_doc, plafond)
        readme_ok = maj_readme(cov)
        print(f"→ site/couverture.json + couverture.js + perimetre.html + methode.html + plafond.html{' + README (tableau)' if readme_ok else ''}")

if __name__ == "__main__": main()
