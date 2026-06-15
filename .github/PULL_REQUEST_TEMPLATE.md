## What And Why

Describe the change and why it matters for the hackathon or data-readiness workflow.

## Risk And Impact

- Data contracts changed:
- Tables affected:
- Known data-quality caveats:

## Tests

- [ ] `python -m compileall -q src notebooks tests`
- [ ] `pytest`
- [ ] `black --check .`
- [ ] `isort --check-only .`
- [ ] `ruff check .`
- [ ] `mypy --strict .`
- [ ] `pylint --fail-under=9.5 src tests`
- [ ] `bandit -r src notebooks -ll`
- [ ] `databricks bundle validate --target dev`

## Notes For Demo

Add screenshots, notebook links, or Databricks job run links when relevant.
