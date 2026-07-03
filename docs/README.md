# SAE Feature Browser (GitHub Pages site)

Interactive dashboard that shows **which sparse-autoencoder (SAE) features a linear
classifier relies on** to infer an author's traits from their comments, for each
characteristic studied in the TFM:

| Tab | Characteristic | Model behind the SAE | Classes |
|-----|----------------|----------------------|---------|
| Sex | female / male | GPT-2 (layer 8) | 2 |
| Age | 14–19 / 20–29 / 30–39 / 40+ | Qwen3-4B-Base (layer 25) | 4 |
| Introvert vs Extravert | I / E | GPT-2 (layer 8) | 2 |
| Intuitive vs Sensing | N / S | Qwen3-4B-Base (layer 25) | 2 |
| Thinking vs Feeling | T / F | Qwen3-4B-Base (layer 25) | 2 |
| Perceiving vs Judging | P / J | GPT-2 (layer 8) | 2 |

> Qwen SAE interpretability had been computed for **age, intuitive and thinking**.
> For **sex, introverted and perceiving** the site falls back to the existing
> **GPT-2** interpretability runs (each tab is labelled with the model it came from).
> To switch those three to Qwen, run their `interpretabilidad_*_qwen_sae.py` scripts
> and re-run the build (see below).

## What each tab shows

1. **Top 5 features per class/pole** of the linear classifier (the SAE latents with
   the largest weight toward that class), each with an auto-generated **name +
   description** and its top activating tokens.
2. Selecting a feature opens up to **8 real comments** where it fires most strongly —
   **de-duplicated** and filtered to **longer comments** (≥5 words / ≥25 chars) — with the
   top tokens **highlighted** and the per-comment activation shown.
3. A closing panel explaining how reading these features lets the model classify the
   characteristic — with an honest caveat that many top features key on *surface
   cues* (topic words, MBTI type codes, orthographic fragments).

The 5 features per pole are the highest-weighted ones that actually have long, unique
example comments; empty/inactive latents are skipped and back-filled from the next
best (the source analysis keeps 20 candidates per class).

## Files

- `index.html`, `styles.css`, `app.js` — the static single-page app (no build step).
- `data/site_data.json` — all the data the page reads, produced by the pipeline in
  [`../site_build/`](../site_build/).

## Author links

The header credits **Aitziber Luis** with LinkedIn and GitHub buttons. Set their
destinations by editing the two `href="…"` values in the `<div class="author">` block
of `index.html` (search for the `AUTHOR` comment).

## View locally

```sh
cd docs
python3 -m http.server 8765
# open http://localhost:8765/
```

(Opening `index.html` directly via `file://` will not work — the page `fetch()`es
`data/site_data.json`, which browsers block over `file://`.)

## Publish on GitHub Pages

1. Push these files to `main`.
2. Repo **Settings → Pages → Build and deployment**.
3. Source: **Deploy from a branch**; Branch: **main**, folder: **/docs**; Save.
4. The site appears at `https://<user>.github.io/<repo>/` after a minute or two.

`.nojekyll` is included so GitHub serves the files as-is.

## Regenerating the data

The page is fully driven by `data/site_data.json`. To rebuild it from the
interpretability summaries see [`../site_build/README.md`](../site_build/README.md).
