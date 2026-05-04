# Copilot Instructions

Personal portfolio, blog, and mini-projects site. Stack: **FastAPI** (async), **SQLAlchemy** (async), **PostgreSQL**, **Jinja2** templates, **TailwindCSS**, **Alpine.js**, **HTMX**.

For a full technical reference see [app_description.md](../app_description.md).

## Architecture

```text
app/web/main.py (root app)
├── /api/v1  → app/web/api/main.py    (REST API: auth + users only)
└── /        → app/web/html/main.py   (HTML frontend: all pages)
```

Layer responsibilities:

- `app/web/html/routes/` — HTTP handlers (WTForms validation, auth checks, template rendering)
- `app/services/` — Business logic (`blog/`, `users/`, `media/`, `general/`) — **never import FastAPI or Starlette here**, so services stay testable without an HTTP context
- `app/datastore/` — SQLAlchemy async models (`db_models.py`) and DB session (`database.py`)
- `app/settings.py` — Pydantic `Settings` loaded from `/run/secrets/`, `.env.local`, `.env`

HTML routes auto-discover all modules in `app/web/html/routes/` via `pkgutil`. Each module **must** expose a `router` variable.

## Key Reference Files

| File                                                                   | Purpose                                        |
| ---------------------------------------------------------------------- | ---------------------------------------------- |
| [app/web/main.py](app/web/main.py)                                     | Root app, mounts sub-apps                      |
| [app/constants.py](app/constants.py)                                   | Shared string constants for template context   |
| [app/errors.py](app/errors.py)                                         | Domain exception hierarchy                     |
| [app/settings.py](app/settings.py)                                     | All config via Pydantic Settings               |
| [app/datastore/db_models.py](app/datastore/db_models.py)               | All SQLAlchemy ORM models                      |
| [app/datastore/database.py](app/datastore/database.py)                 | DB engine + `get_db_session` dependency        |
| [app/permissions.py](app/permissions.py)                               | Role/Action-based permission system            |
| [app/web/html/routes/blog.py](app/web/html/routes/blog.py)             | Largest route file — primary pattern reference |
| [app/services/blog/blog_handler.py](app/services/blog/blog_handler.py) | Service layer pattern reference                |
| [tests/conftest.py](tests/conftest.py)                                 | Root test setup, DB management                 |
| [pyproject.toml](pyproject.toml)                                       | All tool config (pytest, ruff, ty, coverage)   |

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
pytest                        # unit + functional only (fast, default)
pytest --integration=local    # also hits local running app
pytest --playwright=local     # also runs Playwright E2E tests
pytest --all                  # everything
```

Tests use a separate Postgres container (`postgres_test`, port 5433). The root [conftest.py](tests/conftest.py) manages the test DB lifecycle automatically.

### Linting & formatting

Run `pre-commit run --all-files` frequently. This applies Ruff formatting/linting and ty type checking. The config is in `.pre-commit-config.yaml`.

### DB migrations

```shell
# Requires a local Postgres instance running first:
python -m scripts.start_local_postgres --migrate head

# Then generate the migration:
python -m scripts.alembic migrate -m "description of migration"
```

## Coding Conventions

### Async DB session

All DB calls use `AsyncSession` injected as `DBSession`. Never instantiate sessions manually — FastAPI manages their lifetime.

```python
# CORRECT — inject DBSession as a dependency
from app.datastore.database import DBSession


async def my_route(db: DBSession) -> ...:
    result = await db.execute(select(MyModel))


# WRONG — never create sessions inside services or routes
async with get_session_maker()() as session:  # don't do this
    ...
```

Services receive `AsyncSession` as a plain argument (not a FastAPI Dependency) so they remain framework-agnostic and testable.

### Authentication in HTML routes

Use `LoggedInUser` when a route requires authentication, `LoggedInUserOptional` when auth is optional. Both are defined in `app/web/auth.py`.

```python
from app.web.auth import LoggedInUser, LoggedInUserOptional


# Route requires a logged-in user
async def my_route(current_user: LoggedInUser) -> ...: ...


# Route works for both authenticated and anonymous users
async def public_route(current_user: LoggedInUserOptional) -> ...: ...
```

### Permission checks

Use the `@requires_permission` decorator with an `Action` enum value. The decorator assumes the route has a `current_user` parameter.

```python
from app.permissions import Action, requires_permission
from app.web.auth import LoggedInUser


@router.get("/blog/create", response_model=None)
@requires_permission(Action.EDIT_BP)
async def create_bp_get(
    request: Request, current_user: LoggedInUser
) -> _TemplateResponse: ...
```

API routes use JWT bearer tokens instead of cookies.

### WTForms for HTML form validation

Use WTForms (not Pydantic) for HTML form validation because WTForms provides per-field error messages that map directly to Jinja2 template form fields. See `app/web/html/wtform_utils/` for custom fields and validators.

```python
# CORRECT — WTForms for HTML form handling
from app.web.html.wtform_utils import Form


class BlogPostForm(Form):
    title = StringField("Title", validators=[validators.data_required()])
    ...


form_data = await request.form()
form = BlogPostForm.load(form_data)
if not form.validate():
    return templates.TemplateResponse(..., status_code=422)
```

### Service layer returns Pydantic models

Services return typed Pydantic response models (not raw DB objects) so callers have a stable, typed interface even when the underlying DB schema changes.

```python
# Service returns a typed response, not a raw ORM object
response: SaveBlogResponse = await blog_handler.save_blog_post(db, input_data)
if not response.success:
    ...  # handle error with response.err_msg, response.field_errors
blog_post = response.blog_post
```

### SQLAlchemy column type annotations

`db_models.py` defines reusable `Annotated` column types at the top of the file. Use them with `Mapped[...]` syntax instead of repeating column arguments.

```python
# CORRECT — use the annotated type aliases
class MyModel(Base):
    id: Mapped[IntPK]
    username: Mapped[StrIndexedUnique]
    bio: Mapped[StrNullable]
    author_id: Mapped[UsersFk]


# WRONG — don't repeat column args inline
id: Mapped[int] = mapped_column(primary_key=True)
```

### Domain exceptions

Raise typed exceptions from `app/errors.py` (not `HTTPException` directly) so the service layer stays HTTP-agnostic. The web error handlers convert them to responses.

```python
from app import errors

# In a service or route:
if not user:
    raise errors.UserNotFoundError
if not blog_post:
    raise errors.BlogPostNotFoundError
```

### Template context keys

Use constants from `app/constants.py` as template context keys — never hardcode the strings.

```python
from app import constants

# CORRECT
return templates.TemplateResponse(
    request,
    "page.html",
    {
        constants.REQUEST: request,
        constants.CURRENT_USER: current_user,
        constants.FORM: form,
    },
)

# WRONG — hardcoded strings
return templates.TemplateResponse(
    request,
    "page.html",
    {
        "request": request,
        "current_user": current_user,
    },
)
```

### Settings and URLs

Three environments: `local`, `docker`, `prod`. Never hardcode URLs — always use `settings.base_url` so the correct base is used per environment.

### Type checking with ty

Use **ty** (Astral ty, not mypy) as the type checker. All functions and methods must have return type annotations. Annotate variables when the type cannot be inferred.

### Docstrings

Docstrings are required on all public modules, classes, and functions except `__init__` and magic methods. Use single backticks (not double) in docstrings and comments.

### No print statements

Never use `print()` in `app/` or `tests/`. Use the standard `logging` module instead.

## Testing Conventions

### pytest config gotchas

`pyproject.toml` sets `addopts = "--reruns 1"` which retries every failed test once, hiding flakiness during debugging. Override when investigating: `pytest --override-ini="addopts=" ...`

`filterwarnings = ["error:::app", "error:::tests", "error:::scripts"]` makes `DeprecationWarning`s from app/test code into hard errors. Any deprecated API usage in `app/` or `tests/` will fail tests.

### Debug scripts and output files

`ai_workspace/` at the project root is `.gitignore`d and safe for debug scripts and output files. Use it instead of `/tmp/` or other shared locations.
