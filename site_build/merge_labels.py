#!/usr/bin/env python3
"""Fusiona las etiquetas (name/description) generadas por IA en site_data.json.

Lee docs/data/labels/part_*.json (cada uno con objetos {key,name,description})
y rellena los campos name/description de cada feature en site_data.json.
La clave es "<char_id>|<class_index>|<latent_id>".
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs" / "data" / "site_data.json"
LABELS_DIR = ROOT / "site_build" / "labels"


def main():
    labels = {}
    for part in sorted(LABELS_DIR.glob("part_*.json")):
        arr = json.loads(part.read_text())
        for item in arr:
            labels[item["key"]] = {
                "name": (item.get("name") or "").strip(),
                "description": (item.get("description") or "").strip(),
            }
    print(f"Etiquetas cargadas: {len(labels)}")

    site = json.loads(SITE.read_text())
    missing = []
    for c in site["characteristics"]:
        for p in c["poles"]:
            for f in p["features"]:
                key = f"{c['id']}|{p['class_index']}|{f['latent_id']}"
                lab = labels.get(key)
                if lab and lab["name"]:
                    f["name"] = lab["name"]
                    f["description"] = lab["description"]
                else:
                    missing.append(key)
                    f["name"] = f"Feature #{f['latent_id']}"
                    f["description"] = "No automatic label available for this feature."

    SITE.write_text(json.dumps(site, ensure_ascii=False, indent=2))
    n = sum(len(p["features"]) for c in site["characteristics"] for p in c["poles"])
    print(f"Features actualizadas: {n - len(missing)}/{n}")
    if missing:
        print(f"Sin etiqueta ({len(missing)}): {missing}")


if __name__ == "__main__":
    main()
