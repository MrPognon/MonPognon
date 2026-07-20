#!/usr/bin/env python3
"""Valide les fichiers data/ et génère site/data.js.
Usage : python3 scripts/build.py [--check]        validation seule, pour la CI
        python3 scripts/build.py --show <id>      affiche un nœud, source résolue (ADR-0005)"""
import json, sys, glob, os

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
    euros_bloc = {}
    for node in arbres:
        bloc = node.get("bloc_univers")
        if not bloc:
            continue
        niveaux = node.get("niveaux") or []
        # Une fiche communale porte un montant racine null (ADR-0004 : dépenses et
        # recettes ne s'additionnent pas). On analyse alors le volet demandé, en
        # décalant la profondeur d'un cran pour rester aligné sur la table `niveaux`.
        cible, decalage = node, 0
        if node.get("montant") is None:
            cible = next((c for c in node.get("enfants", []) if c["id"].endswith("." + volet)), None)
            decalage = 1
        if cible is None:
            continue
        d = euros_bloc.setdefault(bloc, {})
        for prof, euros in couverture(cible)["profondeurs"].items():
            n = niveau_effectif(niveaux, int(prof) + decalage)
            d[n] = d.get(n, 0.0) + euros

    # 2) C, et ventilation des euros d'univers par niveau
    univers = denom["total_brut_eur"]
    numerateur = raccorde = 0.0
    histo_univers = {n: 0.0 for n in NIVEAUX_P}
    histo_couvert = {n: 0.0 for n in NIVEAUX_P}
    blocs = []
    for seg in denom["segments"]:
        for ss in seg["sous_segments"]:
            ref, couvert = ss.get("referentiel_comptage"), ss.get("couvert_referentiel_eur")
            c = (couvert / ref["total_eur"]) if (ref and couvert) else 0.0
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
            histo_univers["P0"] += ss["poids_eur"] - comptes   # non couvert = P0
            blocs.append({
                "code": ss["code"], "label": ss["label"],
                "poids_eur": ss["poids_eur"], "coefficient": round(c, 6),
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


def main():
    data, fiches, seen = {}, {}, set()
    flux_docs, denominateurs = {}, {}
    communes_dir = os.path.join(ROOT, "data", "collectivites", "communes") + os.sep
    flux_dir = os.path.join(ROOT, "data", "flux") + os.sep
    denom_dir = os.path.join(ROOT, "data", "denominateurs") + os.sep
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True)):
        key = os.path.relpath(f, os.path.join(ROOT, "data")).replace(os.sep, "_").removesuffix(".json")
        with open(f, encoding="utf-8") as fh:
            node = json.load(fh)
        if f.startswith(denom_dir):         # dénominateurs C·P (ADR-0006) : pas des arbres
            valider_denominateur(node, os.path.relpath(f, ROOT))
            denominateurs[node.get("volet", "?")] = node
            continue
        if f.startswith(flux_dir):          # flux (ADR-0001) : validés après les arbres
            flux_docs[os.path.relpath(f, ROOT)] = node
            continue
        resoudre_sources(node, os.path.relpath(f, ROOT))
        validate(node, os.path.relpath(f, ROOT), seen)
        # Fiches communales (ADR-0004) : validées comme le reste, publiées en
        # fragments individuels chargés à la demande — jamais dans data.js.
        if f.startswith(communes_dir):
            fiches[os.path.basename(f).removesuffix(".json")] = node
        else:
            data[key] = node
    for path, doc in flux_docs.items():
        valider_flux(doc, path, seen)
    # Qualification C·P : validée APRÈS la boucle, le dénominateur devant être chargé
    codes = {ss["code"] for d in denominateurs.values()
             for seg in d["segments"] for ss in seg["sous_segments"]}
    for cle, node in list(data.items()) + list(fiches.items()):
        valider_racine_cp(node, cle, codes)
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
    for w in warnings: print("AVERTISSEMENT:", w)
    if errors:
        for e in errors: print("ERREUR:", e, file=sys.stderr)
        sys.exit(1)
    extra = f" + {len(fiches)} fiche(s) communale(s)" if fiches else ""
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
            frag_dir = os.path.join(ROOT, "site", "data", "communes")
            os.makedirs(frag_dir, exist_ok=True)
            for insee, node in sorted(fiches.items()):
                with open(os.path.join(frag_dir, insee + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(node, fh, ensure_ascii=False)
            print(f"→ {frag_dir}{os.sep} ({len(fiches)} fragment(s))")
            with open(os.path.join(ROOT, "site", "communes-index.js"), "w", encoding="utf-8") as fh:
                fh.write("// Généré par scripts/build.py — NE PAS ÉDITER À LA MAIN (éditez data/)\n")
                idx = [{"i": insee, "n": n["label"].split(" (")[0]} for insee, n in sorted(fiches.items())]
                fh.write("window.COMMUNES_IDX = " + json.dumps(idx, ensure_ascii=False) + ";\n")
        # Baromètre de couverture (issue #15) — par arbre, jamais sommé entre arbres.
        cov = {k: couverture(n) for k, n in data.items()}
        cov_doc = {"methode": METHODE_COUVERTURE, "arbres": cov}
        # Indice C·P (ADR-0006) : mesuré contre l'univers réel des APU, pas
        # contre ce qui est déjà modélisé. C'est lui qui va à côté du titre.
        if "depenses" in denominateurs:
            cov_doc["cp"] = indice_cp(list(data.values()) + list(fiches.values()),
                                      denominateurs["depenses"])
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
        readme_ok = maj_readme(cov)
        print(f"→ site/couverture.json + couverture.js{' + README (tableau)' if readme_ok else ''}")

if __name__ == "__main__": main()
