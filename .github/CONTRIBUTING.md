# Contributing

This hackathon project is optimized for fast collaboration while keeping data-quality and reproducibility decisions reviewable.

## Table of Contents

- [Development Setup](#development-setup)
- [Validation](#validation)
- [Commit Style](#commit-style)
- [Databricks Asset Bundle Note](#databricks-asset-bundle-note)

## Development Setup

Use Python 3.14 or newer. The project declares local development tools in [pyproject.toml](../pyproject.toml).

Install development dependencies with your preferred Python package manager. `uv` is recommended:

```bash
uv sync --extra dev
```

## Validation

Run the checks that are available in your environment before opening a pull request:

```bash
python -m compileall -q src notebooks tests
pytest
black --check .
isort --check-only .
ruff check .
mypy --strict .
pylint --fail-under=9.5 src tests
bandit -r src notebooks -ll
databricks bundle validate --target dev
```

## Commit Style

Use Conventional Commits:

```text
feat(databricks): add district readiness scoring
fix(pipeline): preserve ambiguous PIN geography
docs(demo): clarify data readiness narrative
```

Commit signing is expected unless the repository owner documents an explicit exception.

## Databricks Asset Bundle Note

This repository intentionally keeps [databricks.yml](../databricks.yml) with the `.yml` extension because that is the standard Databricks Asset Bundle entrypoint used by the Databricks CLI. Other YAML files use the `.yaml` extension.
