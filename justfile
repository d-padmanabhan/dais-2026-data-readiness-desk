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

# Bootstrap Unity Catalog objects and upload available source files
bootstrap-databricks warehouse_id:
    ./scripts/bootstrap_databricks_workspace.sh --warehouse-id {{warehouse_id}}

# Grant read access to the project catalog and source Volume
grant-catalog-read principal warehouse_id:
    ./scripts/grant_catalog_read_access.sh --principal {{principal}} --warehouse-id {{warehouse_id}}

# Query key cached readiness outputs
query-readiness warehouse_id:
    ./scripts/query_readiness_outputs.sh --warehouse-id {{warehouse_id}}

# Generate SRS state CSV from the SRS bulletin PDF
generate-srs:
    uv run python scripts/generate_srs_2020_state_csv.py

# Fetch India district boundary GeoJSON
fetch-boundaries:
    ./scripts/fetch_district_boundaries.sh

# Fetch India PIN directory using the official OGD API
fetch-pincode:
    ./scripts/fetch_pincode_directory.sh

# Run workflow linting
lint-workflows:
    actionlint .github/workflows/*.yaml

# Run all local CI checks
ci: lint-workflows lint typecheck test
    uv run bandit -r src notebooks -ll
    python -m compileall -q src notebooks tests
