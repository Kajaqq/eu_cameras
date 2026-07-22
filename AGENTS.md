# Repository Guidelines

## Project Structure & Module Organization

HighwayView is a Python 3.14 camera and traffic-alert pipeline. The camera workflow starts in `main.py`; the DATEX II / CCISS overlay workflow starts in `get_datex.py`. Constants, source URLs, output paths, and tuning values live in `config.py`.

- `Downloaders/`: country-specific network fetchers and downloader bases.
- `Parsers/`: country-specific camera parsers that normalize provider data.
- `DatexParser/`: traffic-alert models, DATEX parsing, CCISS parsing, filtering, and overlay export.
- `tools/`: CLI stages for camera checking, loop selection, and HTML generation.
- `data/`: generated JSON, sampled media, slideshow output, and overlay assets.
- `docs/`: architecture notes and generated API documentation.

Treat generated files under `data/` as runtime output. Source behavior belongs in Python modules, config, docs, or static overlay files.

## Architecture Reference

Read `docs/Architecture.md` before changing pipeline ownership, dataflow, module responsibilities, or shared data contracts. It explains what each stage owns, why the split exists, and where to make common changes.

## Build, Test, and Development Commands

Use `uv` for dependency and command execution.

```bash
uv sync --group dev
uv run main.py
uv run get_datex.py --once
uv run tools/camera_check.py data/france_original.json
uv run tools/create_html.py data/cameras_es_online.json --highways AP-7,A-7
uv run ruff check .
uv run ruff format .
uv run ty check .
```

`uv sync --group dev` installs dependencies. 
`main.py` runs the full camera pipeline. 
`get_datex.py --once` writes overlay data once. 
Use focused tool commands when changing one stage.

## Coding Style & Naming Conventions

Follow existing Python style: 4-space indentation, type annotations, `pathlib.Path` for paths, and async I/O for network-heavy code. Keep ownership clear: downloaders fetch, parsers normalize, tools process normalized data, and `config.py` owns provider constants. Ruff targets Python 3.14 with pyupgrade, async, pathlib, performance, and try-rule checks.

## Testing Guidelines

Validate changes with `uv run ruff check .`, `uv run ty check .`, and a focused runtime command. 
For syntax-only checks, use `uv run python -m py_compile <file.py>`. 
If adding tests later, prefer `pytest` under `tests/` with names like `test_datex_parser.py`.

## Commit & Pull Request Guidelines

Git history uses short, imperative subjects such as `Add retry logic for DATEX HTTP downloader` and `Fix Spain camera URL.` Keep commits scoped to one behavior change. Pull requests should describe the changed pipeline path, list validation commands, note excluded generated `data/` artifacts, and link any issue or provider change.

## Agent-Specific Instructions

Before adding code, check whether existing downloader, parser, or tool logic can be reused or simplified. Read `docs/Architecture.md` for pipeline ownership. For Gemini API work, use the `gemini-api` skill first; for Python tooling changes, follow `modern-python-slim`.
