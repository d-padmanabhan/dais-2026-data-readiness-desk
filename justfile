set shell := ["bash", "-euc"]
set dotenv-load := true

# Show available recipes
default:
    @just --list

# Install development dependencies
install:
    uv sync --extra dev

# Format Python code
fmt:
    uv run black .
    uv run isort .

# Run lint checks
lint:
    uv run ruff check .
    uv run pylint --fail-under=9.5 src tests

# Run type checks
typecheck:
    uv run mypy --strict .

# Run unit tests
test:
    uv run pytest -q

# Validate the Databricks bundle for a target
validate-bundle target="dev":
    databricks bundle validate --target {{target}}

# Run workflow linting
lint-workflows:
    actionlint .github/workflows/*.yaml

# Run all local CI checks
ci: lint-workflows lint typecheck test
    uv run bandit -r src notebooks -ll
    python -m compileall -q src notebooks tests
