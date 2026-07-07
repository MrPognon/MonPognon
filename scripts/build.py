#!/usr/bin/env python3
"""Valide les fichiers data/ et génère site/data.js.
Usage : python3 scripts/build.py [--check]  (--check : validation seule, pour la CI)"""
import json, sys, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUTS = {"confirme", "estime", "inconnu"}
errors, warnings = [], []

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

def main():
    data, fiches, seen = {}, {}, set()
    communes_dir = os.path.join(ROOT, "data", "collectivites", "communes") + os.sep
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True)):
        key = os.path.relpath(f, os.path.join(ROOT, "data")).replace(os.sep, "_").removesuffix(".json")
        with open(f, encoding="utf-8") as fh:
            node = json.load(fh)
        validate(node, os.path.relpath(f, ROOT), seen)
        # Fiches communales (ADR-0004) : validées comme le reste, publiées en
        # fragments individuels chargés à la demande — jamais dans data.js.
        if f.startswith(communes_dir):
            fiches[os.path.basename(f).removesuffix(".json")] = node
        else:
            data[key] = node
    for w in warnings: print("AVERTISSEMENT:", w)
    if errors:
        for e in errors: print("ERREUR:", e, file=sys.stderr)
        sys.exit(1)
    extra = f" + {len(fiches)} fiche(s) communale(s)" if fiches else ""
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

if __name__ == "__main__": main()
