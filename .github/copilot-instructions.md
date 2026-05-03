# Copilot Instructions

## Project Overview

Personal portfolio, blog, and mini-projects site ([codewithteddy.dev](https://codewithteddy.dev)). Built with **FastAPI** (async), **SQLAlchemy** (async), **PostgreSQL**, **Jinja2** templates, **TailwindCSS**, **Alpine.js**, and **HTMX**.

## Architecture

The app is a single FastAPI process with two **sub-apps mounted** at the root:

```text
app/web/main.py (root app)
├── /api/v1  → app/web/api/main.py    (REST API: auth + users only)
└── /        → app/web/html/main.py   (HTML frontend: all pages)
```

**Layer responsibilities:**

- `app/web/html/routes/` — HTTP handlers (WTForms validation, auth checks, template rendering)
- `app/services/` — Business logic (`blog/`, `users/`, `media/`, `general/`) — no web framework imports
- `app/datastore/` — SQLAlchemy async models (`db_models.py`) and DB session (`database.py`)
- `app/settings.py` — Pydantic `Settings` loaded from `/run/secrets/`, `.env.local`, `.env`

HTML routes auto-discover and register all modules in `app/web/html/routes/` via `pkgutil`. Each module must expose a `router` variable.

## Developer Workflows

### Local development

```shell
# Start DB (Docker Postgres) + seed dummy data
python -m scripts.start_local_postgres --migrate head

# Start app (requires tmux): runs Tailwind watcher + uvicorn with hot-reload
./scripts/run-dev.sh
```

### Running tests

```shell
# Unit + functional tests only (default, fast)
pytest

# Include integration tests against local env
pytest --integration=local

# Include Playwright E2E tests
pytest --playwright=local

# Run all tests
pytest --all
```

Tests use a **separate Postgres container** (`postgres_test`, port 5433). The root [conftest.py](tests/conftest.py) creates/tears down the test DB automatically.

### Linting & formatting

```shell
pre-commit run --all-files
```

### DB migrations

Database migrations use alembic to generate and run migrations. When a database migration is needed, use the following to generate a new migration file:

```shell
python -m scripts.alembic migrate -m "description of migration"
```

Note: You'll need a local Postgres instance running to generate the migration against. You can use the same local Postgres instance used for development:

```shell
python -m scripts.start_local_postgres --migrate head
```

## Key Conventions

**Async everywhere**: All DB calls use `AsyncSession` injected via FastAPI `Depends(get_db_session)` aliased as `DBSession`. Services accept `AsyncSession` directly—never create their own sessions.

**Authentication**: HTML routes use `LoggedInUser` / `LoggedInUserOptional` FastAPI dependencies (defined in `app/web/auth.py`). Permissions checked with `@requires_permission(Action.X)` decorator. API uses JWT tokens.

**WTForms for HTML forms**: HTML routes use WTForms (not Pydantic) for form validation. See `app/web/html/wtform_utils/` for custom fields and validators.

**Service layer returns typed models**: Services return Pydantic response models (e.g., `SaveBlogResponse`) rather than raw DB objects where possible.

**SQLAlchemy type annotations**: `db_models.py` defines reusable annotated column types at the top (e.g., `IntPK`, `StrUnique`, `UsersFk`) used with `Mapped[IntPK]` syntax.

**Settings**: Three environments — `local`, `docker`, `prod`. Never hardcode URLs; use `settings.base_url`.

**Ruff** is the linter+formatter (100-char line length, extensive rule set). Docstrings required everywhere except `__init__` and magic methods. No `print` statements in app/tests.

**ty** is the type checker (Astral ty, not mypy). All functions/methods must have return type annotations. Variable annotations required when the type cannot be inferred.

**Pre-commit hooks** run Ruff and ty and some other lint hooks. Run `pre-commit run --all-files` to apply all hooks locally.

## Key Files

| File                                                                   | Purpose                                      |
| ---------------------------------------------------------------------- | -------------------------------------------- |
| [app/web/main.py](app/web/main.py)                                     | Root app, mounts sub-apps                    |
| [app/settings.py](app/settings.py)                                     | All configuration via Pydantic Settings      |
| [app/datastore/db_models.py](app/datastore/db_models.py)               | All SQLAlchemy ORM models                    |
| [app/datastore/database.py](app/datastore/database.py)                 | DB engine + `get_db_session` dependency      |
| [app/permissions.py](app/permissions.py)                               | Role/Action-based permission system          |
| [app/web/html/routes/blog.py](app/web/html/routes/blog.py)             | Largest route file; good pattern reference   |
| [app/services/blog/blog_handler.py](app/services/blog/blog_handler.py) | Service layer example                        |
| [tests/conftest.py](tests/conftest.py)                                 | Root test setup, DB management               |
| [pyproject.toml](pyproject.toml)                                       | All tool config (pytest, ruff, ty, coverage) |

## Testing Conventions

### pytest config gotchas

- `pyproject.toml` sets `addopts = "--reruns 1"` — this retries every failed test once, which hides ordering issues and slows debugging. Override it when investigating failures: `pytest --override-ini="addopts=" ...`
- `filterwarnings = ["error:::app", "error:::tests", "error:::scripts"]` — `DeprecationWarning`s from app/test code are **errors**. Any deprecated API usage in `app/` or `tests/` will cause test failures.
- `ai_workspace/` at the project root is in `.gitignore` and safe for writing debug scripts and output files.

## DO these things

- Run `pre-commit run --all-files` frequently to apply all linters and formatters locally. The `pre-commit` config is in `.pre-commit-config.yaml`
- Use single backticks for docstrings and comments rather than double backticks.
- `ai_workspace/` at the project root is in `.gitignore` and is safe for writing debug scripts and output files. Use this directory instead of writing to `/tmp/` or other shared locations.
