# data.bs.ch website mirror + llms.txt toolkit

Repository with two responsibilities for `data.bs.ch`: preserving page/source assets and generating/validating LLM-facing docs.

## What this repository does

- Stores mirrored page/source code from `data.bs.ch` (for example `pages/`, `look_feel/`, `custom_views/`).
- Publishes a concise root `llms.txt` router.
- Generates dataset indexes for LLM navigation:
  - `llms/datasets/index.md`
  - `llms/datasets/by-theme/index.md`
  - `llms/datasets/by-theme/*.md`
  - `llms/datasets/full/index.md`
  - `llms/datasets/full/all.md`
  - `llms/datasets/full/*.md`
- Generates expanded context bundles from `llms.txt`:
  - `llms-ctx.txt` (without `## Optional`)
  - `llms-ctx-full.txt` (with `## Optional`)
- Validates required structure and links before publishing.

## Architecture

- `llms.txt`: root routing manifest for LLMs.
- `llms/*.md`: hand-authored guides.
- `scripts/generate_dataset_docs.py`: builds dataset index pages.
- `scripts/validate_llms_docs.py`: checks required files/sections and link integrity.
- `.github/workflows/validate-llms-docs.yml`: CI validation workflow.
- `.github/workflows/refresh-llms-datasets.yml`: scheduled generation + PR workflow.

## Data source strategy

`scripts/generate_dataset_docs.py` uses the public Explore API only:

- `https://data.bs.ch/api/explore/v2.1/catalog/datasets`

Only public datasets are indexed.

## Prerequisites

- `uv` installed
- Python `3.12+` (see `.python-version`)

## Setup (uv)

```bash
uv sync
```

## Common commands (uv)

Generate dataset docs:

```bash
uv run python scripts/generate_dataset_docs.py
```

Generate llms ctx artifacts:

```bash
uv run python scripts/generate_llms_ctx.py
```

Validate docs:

```bash
uv run python scripts/validate_llms_docs.py
```

## CI behavior

- Validation workflow (`validate-llms-docs.yml`):
  - `uv sync --frozen`
  - generate docs
  - validate docs and links
- Refresh workflow (`refresh-llms-datasets.yml`):
  - scheduled daily
  - regenerates dataset docs and ctx artifacts
  - opens a PR with generated changes

## Publish/deploy checklist

1. Ensure root file is reachable at `/llms.txt`.
2. Ensure linked docs are reachable at:
   - `/llms/getting-started.md`
   - `/llms/odsql-cheatsheet.md`
   - `/llms/query-cookbook.md`
   - `/llms/datasets/index.md`
3. Run local generate + validate commands.
4. Confirm CI passes.
5. Spot-check a few generated theme pages and dataset rows.

## Troubleshooting

- Missing required root links in validator
  - Ensure `llms.txt` includes absolute URLs for all critical docs.
- Broken local links
  - Run validator and fix target paths in markdown.
- Dataset count changes unexpectedly
  - Verify portal availability and Explore API connectivity.
