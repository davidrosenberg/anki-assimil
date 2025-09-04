# Repository Guidelines

## Project Structure & Module Organization
- Root: `README.md` (overview), `CLAUDE.md` (dev tips).
- Active code lives in versioned folders:
  - `v2/` (current CLI): `main.py`, `src/`, `input/`, `data/` (human‑edited), `generated/` and/or `output/` (auto‑generated), `test-data/` (sample media).
  - `v3/` (in development): `main.py`, `src/`, `config.yaml`, `data/`.
  - `v1/` (legacy): original scripts for reference; do not modify.

## Build, Test, and Development Commands
- Setup (v2):
  - `cd v2 && python3 -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Core workflow (v2):
  - `python main.py status` — verify paths and files.
  - `python main.py extract-audio --lessons 1-5` — parse MP3s → initial CSV.
  - `python main.py match-words` — suggest vocab matches.
  - `python main.py export-anki` — create Anki import CSV.
- V3 preview:
  - `cd v3 && pip install -r requirements.txt && python main.py status`

## Coding Style & Naming Conventions
- Language: Python 3; follow PEP 8; 4‑space indentation; prefer type hints.
- Modules/files: `lower_snake_case.py`; functions/vars: `lower_snake_case`; classes: `CamelCase`.
- CLI: Typer commands grouped in `main.py`; keep command names short (`match-words`, `apply_tags`).
- Formatting: keep diffs minimal; if you use formatters (e.g., Black/Ruff), do not commit sweeping reflows without discussion.

## Testing Guidelines
- No formal test suite yet. Validate with sample assets in `v2/test-data/`:
  - Run `python main.py status` and inspect generated CSVs in `generated/` or `output/`.
- When adding non‑trivial logic, include small unit tests under `v2/tests/` (pytest) and document how to run them (`pytest -q`).

## Commit & Pull Request Guidelines
- Commits: imperative mood, scoped prefix when helpful, e.g. `v2: match-words handles niqqud`, `v3: add anki status check`.
- PRs: include purpose, scope, and testing notes; link issues; attach example commands and snippets of generated output.
- Keep `v1/` unchanged; prefer changes in `v2/` (current) or `v3/` (experimental).

## Security & Configuration Tips
- Do not commit personal decks, proprietary MP3s, or large media. `.gitignore` covers common cases.
- Configure paths in `v2/input/config.yaml` or `v3/config.yaml`; keep AnkiConnect URL local.
- Generated files belong in `generated/`/`output/` (v2) or `data/` (v3) and may be safely regenerated.

