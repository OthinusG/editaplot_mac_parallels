# Project Instructions

## Scope

EditaPlot is a Python 3.10–3.12 workflow that drives Origin on Windows to produce editable scientific figures.

## Commands

- Run tests: `python -m pytest`
- Run lint: `python -m ruff check .`
- Windows launcher: `editaplot.cmd`

## Conventions

- Keep changes focused and reuse existing runtime helpers and contracts.
- Preserve the Windows 10/11 x64 compatibility baseline unless a task explicitly expands it.
- Never claim Origin compatibility without a real Origin smoke test and the repository's existing verification gates.
- Do not hard-code credentials or expose local paths, account names, or raw COM errors in diagnostics.
- Follow the style and dependency constraints in `pyproject.toml` and `runtime/pyproject.toml`.

## Verification

- Run the smallest relevant test set first, then broader tests when the change affects shared runtime behavior.
- Origin integration changes require Windows-side tests; macOS-only static checks are not sufficient evidence.
