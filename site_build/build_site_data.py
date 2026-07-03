#!/usr/bin/env python3
"""Construye los datos estaticos del sitio (GitHub Pages) a partir de los
resumenes de interpretabilidad SAE.

Por cada caracteristica (sexo, edad, y las 4 dimensiones MBTI) extrae, para
cada polo/clase, las 5 features (latentes) mas relevantes del clasificador
lineal entrenado sobre el SAE, junto con sus tokens mas activadores y hasta 8
comentarios de ejemplo.

Salida: docs/data/site_data.json

Las descripciones legibles de cada feature se rellenan despues con
merge_labels.py (etiquetado con IA).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELOS = ROOT / "modelos"
OUT = ROOT / "docs" / "data" / "site_data.json"
PAYLOAD = ROOT / "site_build" / "_features_for_labeling.json"  # entrada para el etiquetado con IA

TOP_FEATURES_PER_POLE = 5
MAX_EXAMPLES = 8
MAX_TEXT_CHARS = 320   # recorta blobs muy largos / repetitivos para visualizacion
MIN_EXAMPLE_CHARS = 25  # "solo comentarios largos": minimo de caracteres
MIN_EXAMPLE_WORDS = 5   # ... y minimo de palabras

_WORD_RE = re.compile(r"\w+")


def _norm(t: str) -> str:
    """Clave de deduplicado: minusculas y solo alfanumerico."""
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def is_long(t: str) -> bool:
    return len(t) >= MIN_EXAMPLE_CHARS and len(_WORD_RE.findall(t)) >= MIN_EXAMPLE_WORDS

# Modelos / SAE usados (de sae-ckpts/*/cfg.json e interpretabilidad_*.py)
MODELS = {
    "Qwen3-4B": {
        "name": "Qwen3-4B-Base",
        "hookpoint": "model.layers.25",
        "layer": 25,
        "d_in": 2560,
        "num_latents": 16384,
        "k": 64,
    },
    "GPT-2": {
        "name": "GPT-2 (openai-community/gpt2)",
        "hookpoint": "transformer.h.8",
        "layer": 8,
        "d_in": 768,
        "num_latents": 16384,
        "k": 64,
    },
}

# Definicion de cada caracteristica: archivo de interpretabilidad, modelo, y
# etiquetas legibles por polo/clase (MBTI: 1 = rasgo presente).
CHARACTERISTICS = [
    {
        "id": "sex",
        "label": "Sex",
        "short": "Sex",
        "icon": "venus-mars",
        "model": "GPT-2",
        "dir": "genero_sae_interpretabilidad",
        "question": "Is the author female or male?",
        "poles": {
            "female": {"label": "Female", "tag": "Female", "tone": "pink"},
            "male": {"label": "Male", "tag": "Male", "tone": "blue"},
        },
    },
    {
        "id": "age",
        "label": "Age",
        "short": "Age",
        "icon": "calendar",
        "model": "Qwen3-4B",
        "dir": "edad_qwen_sae_interpretabilidad",
        "question": "Which age band does the author belong to?",
        "poles": {
            "14_19": {"label": "14 – 19", "tag": "14–19", "tone": "teal"},
            "20_29": {"label": "20 – 29", "tag": "20–29", "tone": "green"},
            "30_39": {"label": "30 – 39", "tag": "30–39", "tone": "amber"},
            "40_plus": {"label": "40 +", "tag": "40+", "tone": "orange"},
        },
    },
    {
        "id": "introverted",
        "label": "Introvert vs Extravert",
        "short": "I / E",
        "icon": "users",
        "model": "GPT-2",
        "dir": "introverted_sae_interpretabilidad",
        "question": "Is the author more introverted or extraverted?",
        "poles": {
            "0": {"label": "Extraversion (E)", "tag": "Extravert", "tone": "amber"},
            "1": {"label": "Introversion (I)", "tag": "Introvert", "tone": "indigo"},
        },
    },
    {
        "id": "intuitive",
        "label": "Intuitive vs Sensing",
        "short": "N / S",
        "icon": "sparkles",
        "model": "Qwen3-4B",
        "dir": "intuitive_qwen_sae_interpretabilidad",
        "question": "Does the author rely more on intuition or sensing?",
        "poles": {
            "0": {"label": "Sensing (S)", "tag": "Sensing", "tone": "green"},
            "1": {"label": "Intuition (N)", "tag": "Intuition", "tone": "violet"},
        },
    },
    {
        "id": "thinking",
        "label": "Thinking vs Feeling",
        "short": "T / F",
        "icon": "brain",
        "model": "Qwen3-4B",
        "dir": "thinking_qwen_sae_interpretabilidad",
        "question": "Does the author lean toward thinking or feeling?",
        "poles": {
            "0": {"label": "Feeling (F)", "tag": "Feeling", "tone": "pink"},
            "1": {"label": "Thinking (T)", "tag": "Thinking", "tone": "blue"},
        },
    },
    {
        "id": "perceiving",
        "label": "Perceiving vs Judging",
        "short": "P / J",
        "icon": "compass",
        "model": "GPT-2",
        "dir": "perceiving_sae_interpretabilidad",
        "question": "Is the author more perceiving or judging?",
        "poles": {
            "0": {"label": "Judging (J)", "tag": "Judging", "tone": "teal"},
            "1": {"label": "Perceiving (P)", "tag": "Perceiving", "tone": "orange"},
        },
    },
]


def clean_text(text: str) -> str:
    text = (text or "").strip()
    # colapsa secuencias de un mismo caracter repetido >6 veces (yesyesyes / aaaa)
    text = re.sub(r"(.)\1{6,}", lambda m: m.group(1) * 6 + "…", text)
    text = re.sub(r"\s+", " ", text)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS].rstrip() + "…"
    return text


def collect_examples(entry, require_long):
    """Ejemplos deduplicados (y opcionalmente solo 'largos') de un latente,
    ordenados por activacion descendente, maximo MAX_EXAMPLES."""
    seen = set()
    out = []
    for ex in entry.get("examples", []):
        txt = clean_text(ex.get("text", ""))
        if not txt:
            continue
        if require_long and not is_long(txt):
            continue
        key = _norm(txt)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"activation": round(float(ex.get("activation", 0.0)), 3), "text": txt})
        if len(out) >= MAX_EXAMPLES:
            break
    return out


def _feature_dict(entry, examples):
    top_words = [w["token"] for w in entry.get("top_words", []) if w.get("token")]
    return {
        "latent_id": int(entry["latent_id"]),
        "score": round(float(entry.get("class_score", 0.0)), 2),
        "coefficient": round(float(entry.get("raw_coefficient", 0.0)), 2),
        "top_words": top_words[:10],
        "highlight": [w.lower() for w in top_words[:10]],
        "examples": examples,
        # rellenado por merge_labels.py
        "name": "",
        "description": "",
    }


def extract_features(entries):
    """Toma las 5 features con mayor class_score que tengan tokens y al menos un
    comentario de ejemplo largo y unico. Descarta features vacias/inactivas y
    rellena (backfill) con las siguientes del top-20. Si por algun motivo no se
    llegan a 5 features 'largas', completa con las mejores restantes (cualquier
    longitud) para garantizar 5 por polo."""
    ranked = sorted(entries, key=lambda e: e.get("class_score", 0.0), reverse=True)
    features = []
    used = set()
    # 1) preferimos features con ejemplos largos y unicos
    for e in ranked:
        if len(features) >= TOP_FEATURES_PER_POLE:
            break
        if not e.get("top_words"):
            continue
        examples = collect_examples(e, require_long=True)
        if not examples:
            continue
        features.append(_feature_dict(e, examples))
        used.add(e["latent_id"])
    # 2) backfill defensivo (no deberia hacer falta con los datos actuales)
    if len(features) < TOP_FEATURES_PER_POLE:
        for e in ranked:
            if len(features) >= TOP_FEATURES_PER_POLE:
                break
            if e["latent_id"] in used or not e.get("top_words"):
                continue
            examples = collect_examples(e, require_long=False)
            if not examples:
                continue
            features.append(_feature_dict(e, examples))
            used.add(e["latent_id"])
    return features


def build():
    characteristics = []
    for spec in CHARACTERISTICS:
        path = MODELOS / spec["dir"] / "interpretabilidad_sae_resumen.json"
        data = json.loads(path.read_text())
        tlc = data["top_latents_by_class"]
        class_names = data["class_names"]
        m = data.get("metrics", {})

        poles = []
        for class_idx, class_name in enumerate(class_names):
            pole_meta = spec["poles"].get(class_name, {"label": class_name, "tag": class_name, "tone": "slate"})
            entries = tlc.get(str(class_idx)) or tlc.get(class_name) or []
            poles.append({
                "class_index": class_idx,
                "class_name": class_name,
                "label": pole_meta["label"],
                "tag": pole_meta["tag"],
                "tone": pole_meta["tone"],
                "features": extract_features(entries),
            })

        characteristics.append({
            "id": spec["id"],
            "label": spec["label"],
            "short": spec["short"],
            "icon": spec["icon"],
            "question": spec["question"],
            "model": spec["model"],
            "model_info": MODELS[spec["model"]],
            "task_name": data.get("task_name"),
            "pooling": data.get("pooling"),
            "num_latents": data.get("num_latents"),
            "num_users_train": data.get("num_users_train"),
            "num_users_eval": data.get("num_users_eval"),
            "num_comments_train": data.get("num_comments_train"),
            "metrics": {
                "accuracy": round(m.get("accuracy", 0.0), 4),
                "balanced_accuracy": round(m.get("balanced_accuracy", 0.0), 4),
                "f1_macro": round(m.get("f1_macro", 0.0), 4),
            },
            "poles": poles,
        })

    out = {
        "generated_by": "site_build/build_site_data.py",
        "title": "SAE feature browser — inferring author traits from comments",
        "models": MODELS,
        "characteristics": characteristics,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # Payload compacto para el etiquetado con IA (merge_labels.py fusiona la salida)
    payload = []
    for c in characteristics:
        for p in c["poles"]:
            for f in p["features"]:
                payload.append({
                    "key": f"{c['id']}|{p['class_index']}|{f['latent_id']}",
                    "characteristic": c["label"],
                    "pole": p["label"],
                    "top_words": f["top_words"][:10],
                    "examples": [e["text"] for e in f["examples"][:8]],
                })
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False))

    n_feat = sum(len(p["features"]) for c in characteristics for p in c["poles"])
    print(f"Escrito {OUT}")
    print(f"  caracteristicas={len(characteristics)} polos={sum(len(c['poles']) for c in characteristics)} features={n_feat}")
    print(f"Escrito {PAYLOAD} ({len(payload)} features para etiquetar)")


if __name__ == "__main__":
    build()
