# Build pipeline for the GitHub Pages site

Turns the SAE interpretability summaries in `modelos/*_sae_interpretabilidad/`
into the single JSON the static site reads (`docs/data/site_data.json`).

## Steps

```sh
# 1. Extract top-5 features per class/pole into docs/data/site_data.json
#    (also writes site_build/_features_for_labeling.json, the labeling input)
python3 site_build/build_site_data.py

# 2. (AI labeling) Produce a human-readable name + description per feature.
#    site_build/_features_for_labeling.json -> site_build/labels/part_*.json
#    Each part_*.json is a JSON array of {key, name, description}, where
#    key = "<characteristic_id>|<class_index>|<latent_id>".
#    The committed labels were generated with an LLM; edit them by hand anytime.

# 3. Merge the labels into docs/data/site_data.json
python3 site_build/merge_labels.py
```

After step 3, reload the site — no other build step is needed.

## Which characteristic maps to which file

Defined in `CHARACTERISTICS` inside `build_site_data.py`:

| id | label | source dir | model |
|----|-------|-----------|-------|
| `sex` | Sex | `genero_sae_interpretabilidad` | GPT-2 |
| `age` | Age | `edad_qwen_sae_interpretabilidad` | Qwen3-4B |
| `introverted` | Introvert vs Extravert | `introverted_sae_interpretabilidad` | GPT-2 |
| `intuitive` | Intuitive vs Sensing | `intuitive_qwen_sae_interpretabilidad` | Qwen3-4B |
| `thinking` | Thinking vs Feeling | `thinking_qwen_sae_interpretabilidad` | Qwen3-4B |
| `perceiving` | Perceiving vs Judging | `perceiving_sae_interpretabilidad` | GPT-2 |

### Switching sex / introverted / perceiving to Qwen

1. Run the corresponding Qwen interpretability scripts so the output dirs appear:
   - `clasificacion_genero/gpt_qwen_activaciones/interpretabilidad_genero_qwen_sae.py`
     → `modelos/genero_qwen_sae_interpretabilidad/`
   - `clasificacion_mbti/introverted/interpretabilidad_introverted_qwen_sae.py`
     → `modelos/introverted_qwen_sae_interpretabilidad/`
   - `clasificacion_mbti/perceiving/interpretabilidad_perceiving_qwen_sae.py`
     → `modelos/perceiving_qwen_sae_interpretabilidad/`
2. In `build_site_data.py`, change those three entries' `"dir"` to the new
   `*_qwen_sae_interpretabilidad` folders and `"model"` to `"Qwen3-4B"`.
3. Re-run steps 1–3 above.

## Feature & example selection (in `build_site_data.py`)

- For each class the script ranks the 20 candidate latents by classifier weight and
  keeps the **top 5 that have at least one long, unique example** — so empty/inactive
  latents are dropped and back-filled automatically.
- Example comments are **de-duplicated** (case/punctuation-insensitive) and filtered to
  **long comments** via `MIN_EXAMPLE_CHARS` (25) and `MIN_EXAMPLE_WORDS` (5). Tune those
  constants to loosen/tighten the filter.
- If re-pointing characteristics or changing thresholds adds/removes features, re-run the
  AI labeling (step 2) for the new ones, or relabel all 70 from the regenerated
  `_features_for_labeling.json`.

## Notes / limitations

- Each feature shows up to **8** example comments (the interpretability runs were
  generated with `TOP_EXAMPLES_PER_LATENT = 8`, and the long/unique filter can leave
  fewer). Increase that constant in `interpretabilidad_sae_qwen_common.py` /
  `interpretabilidad_sae_common.py` and re-run the interpretability analysis to get more.
- The stored data has a single activation value **per comment**, not per token.
  The site therefore highlights occurrences of each feature's top tokens as an
  approximation of token-level attribution (true per-token highlighting would
  require re-running activation extraction on GPU).
