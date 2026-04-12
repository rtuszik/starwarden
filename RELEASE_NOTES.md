# Starwarden v2.0.0 - Release Notes

> Changes since [v1.4.0](https://github.com/rtuszik/starwarden/releases/tag/v1.4.0) (2025-07-04)

---

## Breaking Changes

### Python 3.13+ Required
The minimum supported Python version is now **3.13**. Python 3.12 and earlier are no longer supported.

### Build System Migrated to uv
`requirements.txt` and pip have been replaced by [`uv`](https://docs.astral.sh/uv/) with a `pyproject.toml`. This affects both local installation and the Docker image:

- **Local**: install with `uv sync` instead of `pip install -r requirements.txt`
- **Docker**: the base image is now `ghcr.io/astral-sh/uv:trixie-slim`; dependencies are installed via `uv sync --locked`

A `uv.lock` file is now committed, ensuring fully reproducible builds.

---

## New Features

### PyPI Package
Starwarden is now published to PyPI on every release. Install it with:
```
uv tool install starwarden
# or
pip install starwarden
```
A `starwarden` console script entry point is provided, so the tool can be invoked directly from the terminal.

### OSSF Scorecard Integration
The repository now participates in the [OpenSSF Scorecard](https://securityscorecards.dev/) program for supply-chain security analysis. Results are published automatically on every push to `main` and on a weekly schedule.

### Automated Test Suite
Initial pytest-based tests have been added under `tests/`:

| File | Coverage |
|---|---|
| `tests/test_main.py` | `build_tags()` tag-building logic |
| `tests/test_linkwarden_api.py` | `upload_link()` and `get_existing_links()` API calls |
| `tests/test_smoke.py` | Package import smoke test |

Tests run automatically on every pull request via a new `pytest` GitHub Actions workflow.

---

## Enhancements

### Code Refactoring
- **Extracted `build_tags()`**: tag-construction logic has been pulled out of `run_update()` into a standalone `build_tags(config_data, repo)` function, making it independently testable.
- **Absolute imports**: all intra-package imports converted from relative (`from .utils`) to absolute (`from starwarden.utils`) style for clarity.
- **Logging constants**: logger configuration values are now defined as module-level constants rather than inline default arguments, improving readability.

### Request Timeouts
HTTP calls to the Linkwarden API (`get_collections`, `upload_link`) now include an explicit **30-second timeout**, preventing the process from hanging indefinitely on unresponsive servers.

### Bug Fix: Apprise URL Validation
The Apprise notification URL check was comparing against the internal `.servers` attribute, which is not part of the public API. This has been corrected to use `len(apobj) == 0`.

### Docker Improvements
- Base image switched from `python:3.12-slim` to the official `uv` image (`ghcr.io/astral-sh/uv:trixie-slim`).
- The cron job and startup script now invoke the package as a Python module (`python -m starwarden.main`) rather than calling the old top-level script.
- `docker-compose.build.yml` has been removed (the main `docker-compose.yml` is sufficient).

### Dependency Management: Dependabot → Renovate
Dependabot has been replaced by [Renovate](https://docs.renovatebot.com/) for automated dependency updates. Renovate provides more granular grouping, better monorepo support, and richer update strategies.

---

## CI/CD

| Workflow | Change |
|---|---|
| `publish.yml` | **New** — builds the package, runs smoke tests on both wheel and sdist, then publishes to PyPI on release |
| `pytest.yml` | **New** — runs the test suite on every pull request and on manual dispatch |
| `scorecard.yml` | **New** — weekly OSSF Scorecard analysis with SARIF upload to the security dashboard |
| `lint.yml` | Updated to use `uv`-based linting (`ruff`) instead of the previous setup |

---

## Dependency Updates

| Package | From | To |
|---|---|---|
| `rich` | 14.0.0 | **15.0.0** |
| `apprise` | 1.9.3 | 1.9.6 |
| `pygithub` | 2.6.1 | 2.8.1 |
| `python-dotenv` | 1.1.1 | 1.2.1 |
| `tqdm` | 4.67.1 | 4.67.3 |
| `urllib3` | 2.5.0 | 2.6.3 |
| `actions/checkout` | v4 | v6 |
| `actions/upload-artifact` | v4.6.1 | v6.0.0 |
| `github/codeql-action` | v3 | v4 |
| `ossf/scorecard-action` | v2.4.1 | v2.4.3 |

**Removed dev dependency**: `bandit` (static security analysis) — removed as redundant given the existing `ruff` and type-checking toolchain.

---

## Migration Guide (v1.4.0 → v2.0.0)

1. **Upgrade Python** to 3.13 or later.
2. **Install uv** if you haven't already: https://docs.astral.sh/uv/getting-started/installation/
3. **Replace pip install** with `uv sync` (or `uv sync --locked` for exact reproducibility).
4. **Docker users**: pull the latest image — no `.env` or configuration changes are required.
5. **Environment variables**: no changes; your existing `.env` file works as-is.
