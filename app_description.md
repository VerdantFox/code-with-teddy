# Application Research: codewithteddy.dev

A comprehensive, unified picture of the full-stack application — back end and front end — and how they are wired together.

---

## Table of Contents

1. [Application Identity & Purpose](#1-application-identity--purpose)
2. [Technology Stack](#2-technology-stack)
3. [Repository & Project Layout](#3-repository--project-layout)
4. [Process Architecture: App Mounting & Middleware](#4-process-architecture-app-mounting--middleware)
5. [Configuration & Secrets](#5-configuration--secrets)
6. [Database Layer](#6-database-layer)
7. [Service Layer (Business Logic)](#7-service-layer-business-logic)
8. [HTTP Layer: HTML Sub-App](#8-http-layer-html-sub-app)
9. [HTTP Layer: REST API Sub-App](#9-http-layer-rest-api-sub-app)
10. [Authentication & Authorization](#10-authentication--authorization)
11. [Front-End System](#11-front-end-system)
12. [Static Assets & Build Pipeline](#12-static-assets--build-pipeline)
13. [Error Handling](#13-error-handling)
14. [Flash Messaging](#14-flash-messaging)
15. [Blog System: End-to-End](#15-blog-system-end-to-end)
16. [User System: End-to-End](#16-user-system-end-to-end)
17. [Media System: End-to-End](#17-media-system-end-to-end)
18. [Security Model](#18-security-model)
19. [Monitoring](#19-monitoring)
20. [Containerization & Deployment](#20-containerization--deployment)
21. [Database Migrations](#21-database-migrations)
22. [Developer Tooling & Testing](#22-developer-tooling--testing)
23. [Full Request Lifecycle](#23-full-request-lifecycle)
24. [Integration Wiring Reference](#24-integration-wiring-reference)

---

## 1. Application Identity & Purpose

**codewithteddy.dev** is Teddy Williams' personal portfolio website. It is a production web application hosting:

- A **personal blog** (markdown-authored posts, series, comments, likes, full-text search)
- A **portfolio** (about page, projects page, experience page)
- Several **mini-project pages** (Connect 4 game, Twisted Towers, Moth Hunt, File Renamer)
- A **REST API** for programmatic access to users

It is a fully server-side rendered, multi-page application (not a SPA) enhanced with targeted JavaScript for interactivity.

---

## 2. Technology Stack

### Back End

| Category        | Technology                                    |
| --------------- | --------------------------------------------- |
| Language        | Python 3.14                                   |
| Web framework   | FastAPI (async)                               |
| ASGI server     | Uvicorn                                       |
| Process manager | Gunicorn                                      |
| ORM             | SQLAlchemy (async)                            |
| Database        | PostgreSQL 16.2                               |
| DB driver       | asyncpg (async), psycopg (Alembic)            |
| Migrations      | Alembic                                       |
| Data validation | Pydantic v2                                   |
| HTML forms      | WTForms                                       |
| Authentication  | PyJWT (HS256), bcrypt (passlib)               |
| Sessions        | Starlette `SessionMiddleware` (itsdangerous)  |
| Templating      | Jinja2 + jinja-partials                       |
| Markdown        | python-markdown, pymdown-extensions, pygments |
| HTML processing | BeautifulSoup4, bleach, micawber              |
| Media           | Pillow                                        |
| Email           | MailerSend                                    |
| Caching         | aiocache                                      |
| Error tracking  | Sentry SDK                                    |
| Settings        | Pydantic `BaseSettings`                       |

### Front End

| Category      | Technology                                                    |
| ------------- | ------------------------------------------------------------- |
| CSS           | TailwindCSS v4 + Typography, Forms, Container Queries plugins |
| Reactivity    | Alpine.js (with focus, intersect, morph, persist plugins)     |
| AJAX          | HTMX 1.9.12 (pinned)                                          |
| Tooltips      | Tippy.js + Popper.js                                          |
| Modals        | SweetAlert2                                                   |
| Notifications | Simple-Notify                                                 |
| GIF handling  | Freezeframe                                                   |
| Fonts         | Roboto via fonts.bunny.net                                    |

### Infrastructure

| Category         | Technology                    |
| ---------------- | ----------------------------- |
| Reverse proxy    | Caddy 2.10                    |
| Containerization | Docker + Docker Compose       |
| Secrets          | Docker secrets + `.env` files |

---

## 3. Repository & Project Layout

```txt
code-with-teddy/
├── app/                         # Application source code
│   ├── constants.py             # Shared constants
│   ├── errors.py                # Domain exception hierarchy
│   ├── mixins.py                # AuthUserMixin
│   ├── permissions.py           # Role/Action-based authorization
│   ├── settings.py              # Pydantic Settings (all config)
│   ├── datastore/
│   │   ├── database.py          # Engine, session, DBSession dependency
│   │   └── db_models.py         # All SQLAlchemy ORM models
│   ├── services/
│   │   ├── blog/                # Blog business logic + markdown pipeline
│   │   ├── general/             # Auth helpers, encryption, email, transforms
│   │   ├── media/               # Media upload, PIL processing
│   │   └── users/               # User registration, update, password reset
│   └── web/
│       ├── auth.py              # JWT + cookie auth dependencies
│       ├── field_types.py       # Annotated FastAPI field types
│       ├── main.py              # Root app (mounts sub-apps)
│       ├── monitoring.py        # Sentry initialization
│       ├── web_models.py        # UnauthenticatedUser, Token
│       ├── api/                 # REST API sub-app
│       │   ├── main.py
│       │   ├── api_models.py
│       │   ├── error_handlers.py
│       │   └── routes/
│       │       ├── auth.py      # POST /auth/token
│       │       └── users.py     # CRUD /users
│       └── html/                # HTML sub-app
│           ├── main.py          # Sub-app, route auto-discovery, CSP
│           ├── const.py         # Jinja2 templates singleton
│           ├── error_handlers.py
│           ├── flash_messages.py
│           ├── jinja_globals.py
│           ├── routes/          # Auto-discovered route modules
│           ├── static/          # CSS, JS, media, images
│           ├── templates/       # Jinja2 HTML templates
│           └── wtform_utils/    # WTForms helpers and custom fields
├── caddy/                       # Caddy reverse proxy config
├── docker_config/               # Dockerfile + docker-compose
├── migrations/                  # Alembic migration environment
├── scripts/                     # Dev tooling (alembic wrapper, bundler, deploy, etc.)
├── tests/                       # Pytest test suite
├── pyproject.toml               # All tool config + dependencies
├── ruff.toml                    # Ruff linter config
└── ty.toml                      # ty type checker config
```

---

## 4. Process Architecture: App Mounting & Middleware

The entire application runs as a single Python process. FastAPI's sub-app mounting creates three independent ASGI applications chained together:

```txt
Browser → Caddy (TLS, compression, static files, reverse proxy)
              ↓
     Root FastAPI App  (app/web/main.py)
     ├── SessionMiddleware      ← flash message storage (cookie)
     ├── CORSMiddleware         ← dev-only localhost CORS
     ├── Lifespan               ← DB setup/teardown on startup/shutdown
     │
     ├── /api/v1  ──→  API Sub-App  (app/web/api/main.py)
     │                 ├── AppError → JSON error handler
     │                 └── Routes: /auth/token, /users/**
     │
     └── /        ──→  HTML Sub-App  (app/web/html/main.py)
                       ├── CSPMiddleware  ← per-request nonce
                       ├── AppError → redirect error handler
                       ├── Routes: auto-discovered from routes/**
                       └── /static ──→ StaticFiles
```

### Middleware Details

| Middleware          | Applied to   | Key behavior                                                                                                                                     |
| ------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CORSMiddleware`    | Root app     | Localhost origins only; credentials allowed; all methods/headers                                                                                 |
| `SessionMiddleware` | Root app     | Cookie-signed sessions via itsdangerous; 86400s max age; keyed by `settings.session_secret`                                                      |
| `CSPMiddleware`     | HTML sub-app | Generates `base64(secrets.token_bytes(16))` nonce per request; attaches to `request.state.nonce`; sets `Content-Security-Policy` response header |

### Route Auto-Discovery

The HTML sub-app discovers route modules automatically at startup:

```python
for module_info in pkgutil.iter_modules(routes.__path__):
    module = importlib.import_module(f"app.web.html.routes.{module_info.name}")
    app.include_router(module.router)
```

Every file in `app/web/html/routes/` must expose a `router: APIRouter` variable.

---

## 5. Configuration & Secrets

### `app/settings.py`

All configuration is centralized in a single `Settings(BaseSettings)` instance (imported as `settings`). Pydantic reads values with this priority:

1. Docker secrets from `/run/secrets/<field_name>` (production)
2. `.env.local` (local developer overrides)
3. `.env` (shared defaults)

**Complete field reference:**

| Field                         | Default   | Description                                           |
| ----------------------------- | --------- | ----------------------------------------------------- |
| `environment`                 | —         | `LOCAL`, `DOCKER`, or `PROD`                          |
| `db_connection_string`        | —         | PostgreSQL DSN                                        |
| `db_echo`                     | `False`   | Echo SQL to stdout                                    |
| `db_pool_size`                | `5`       | Connection pool size                                  |
| `db_max_overflow`             | `10`      | Max overflow connections                              |
| `db_create_tables`            | `True`    | Auto-create tables on startup (`False` in Docker)     |
| `jwt_secret`                  | —         | HS256 signing secret                                  |
| `jwt_algorithm`               | `"HS256"` | JWT algorithm                                         |
| `jwt_expires_mins`            | `30`      | Access token lifetime in minutes                      |
| `session_secret`              | —         | Session cookie signing key                            |
| `encryption_key`              | —         | HMAC-SHA256 key (hex bytes) for password reset tokens |
| `mailersend_api_key`          | —         | Transactional email API key                           |
| `my_email_address`            | —         | Admin notification recipient                          |
| `site_email_address`          | —         | From address for emails                               |
| `sentry_dsn`                  | —         | Sentry error reporting DSN                            |
| `sentry_ingest`               | —         | Sentry `connect-src` URL for CSP                      |
| `sentry_cdn`                  | —         | Sentry JS SDK CDN URL                                 |
| `sentry_error_sample_rate`    | —         | Error sampling rate                                   |
| `sentry_traces_sample_rate`   | —         | Tracing sampling rate                                 |
| `sentry_profiles_sample_rate` | —         | Profiling sampling rate                               |

`settings.base_url` returns `http://localhost` (LOCAL), `https://codewithteddy.dev` (PROD), etc.

---

## 6. Database Layer

### Engine & Session (`app/datastore/database.py`)

- **`get_engine()`** — singleton `AsyncEngine`; `pool_pre_ping=True`; pool size and overflow from settings.
- **`get_session_maker()`** — singleton `async_sessionmaker`; `expire_on_commit=False` so ORM objects remain usable after commit.
- **`get_db_session()`** — async generator FastAPI dependency; yields a session, auto-closes on request completion.
- **`DBSession`** — `Annotated[AsyncSession, Depends(get_db_session)]`; injected into routes and accepted by service functions.

Sessions are **never** created inside service functions; they are always passed in from route handlers.

### ORM Models (`app/datastore/db_models.py`)

All models live in one file. The `Base` class extends `AsyncAttrs` (for lazy async relationship loading) and `DeclarativeBase` (SQLAlchemy 2.0 style). `str100` maps to `String(100)`.

**Reusable annotated column type aliases:**

| Alias                                  | Type details                                              |
| -------------------------------------- | --------------------------------------------------------- |
| `IntPK`                                | Integer, primary key, autoincrement                       |
| `StrPK`                                | String(100), primary key                                  |
| `StrUnique`                            | String(100), unique                                       |
| `StrIndexedUnique`                     | String(100), unique + indexed                             |
| `StrNullable`                          | String(100), nullable                                     |
| `IntNullable`                          | Integer, nullable                                         |
| `IntIndexed`                           | Integer, indexed                                          |
| `IntIndexedDefaultZero`                | Integer, indexed, server_default `0`                      |
| `DateTimeIndexed`                      | DateTime(timezone=True), indexed, server_default `utcnow` |
| `BoolDefaultFalse` / `BoolDefaultTrue` | Boolean with server defaults                              |
| `UsersFk`                              | Integer, FK → `users.id` CASCADE DELETE                   |
| `BlogPostFK`                           | Integer, FK → `blog_posts.id` CASCADE DELETE              |
| `CommentFK`                            | Integer, FK → `blog_post_comments.id` CASCADE DELETE      |
| `BPSeriesFK`                           | Integer, nullable FK → `blog_post_series.id` SET NULL     |

**Model summary:**

| Model                | Key fields & relationships                                                                                                                                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `User`               | id, username (unique+indexed), email (unique+indexed), full_name, timezone, is_active, avatar_location, password_hash, google_oauth_id, github_oauth_id, role                                                                               |
| `BlogPost`           | id, title (unique), slug (unique), read_mins, is_published, can_comment, markdown/html content+description+toc, likes, views, created/updated timestamps; M2M tags; O2M media, comments, old_slugs; nullable series FK; ts_vector GIN index |
| `OldBlogPostSlug`    | slug (PK), blog_post_id FK; enables redirect lookups for old slugs                                                                                                                                                                          |
| `BlogPostTag`        | tag (PK); M2M to BlogPost via `blog_tags_associations`                                                                                                                                                                                      |
| `BlogPostMedia`      | id, blog_post_id FK, name, locations (ARRAY(String)), media_type, position                                                                                                                                                                  |
| `BlogPostComment`    | id, blog_post_id FK, name, email, guest_id, user_id (nullable), md_content, html_content, likes, timestamps                                                                                                                                 |
| `BlogPostSeries`     | id, name (unique), description; O2M posts ordered by series_position; ts_vector GIN index                                                                                                                                                   |
| `PasswordResetToken` | id, user_id FK, encrypted_query (unique+indexed), created/expires timestamps                                                                                                                                                                |
| `TSVector`           | Custom TypeDecorator wrapping PostgreSQL TSVECTOR                                                                                                                                                                                           |

---

## 7. Service Layer (Business Logic)

Services live in `app/services/` and contain all business logic. They import from `app/datastore` and each other, but **never** from FastAPI or Starlette. All accept `AsyncSession` directly.

### Blog Services (`app/services/blog/`)

#### `blog_handler.py` — CRUD & querying

**Pydantic I/O models:**

- `SaveBlogInput` — `title`, `tags` (CoercedList), `can_comment` (CoercedBool), `is_published`, `description`, `content`, `thumbnail_url`, `series_id`, `series_position`, `likes`, `views`, `existing_bp`
- `SaveBlogResponse` — `success`, `blog_post`, `err_msg`, `status_code`, `field_errors`
- `SaveCommentInput` / `SaveCommentResponse`
- `Paginator` — `blog_posts`, `min_result`, `max_result`, `total_results`, `total_pages`, `current_page`, `is_first/last/only_page`

**Key functions:**

| Function                                                  | Description                                                                                                                        |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `get_blog_posts()`                                        | Paginated query with full-text search (ts_vector), tag filter, order; `COUNT(*) OVER()` window function returns total in one query |
| `get_bp_from_slug()`                                      | Fetch by slug; falls back to `OldBlogPostSlug` history                                                                             |
| `get_bp_from_id()`                                        | Fetch by id; optional `with_for_update()`                                                                                          |
| `save_blog_post()`                                        | Create or update; slug generation, tag sync, markdown render, slug history tracking                                                |
| `get_all_series()` / `get_series_from_id()`               | Series queries with optional full-text search                                                                                      |
| `create_series()` / `update_series()` / `delete_series()` | Series CRUD                                                                                                                        |

**Eager loading:**

- Full-detail queries (`_get_bp_statement`): `selectinload` for tags, media, comments→user, old_slugs, series→posts
- List-view queries (`_get_bp_list_statement`): `selectinload` for tags + comments only

#### `markdown_parser.py` — Markdown → HTML pipeline

Blog post content is converted **once at save time** and stored in the DB. The pipeline:

1. **python-markdown** with extensions: `CodeHilite`, `Extra`, `TocExtension` (depth 3), `Admonition`, `SaneLists`, `Smarty`, `pymdownx.tilde` (~~strikethrough~~), `pymdownx.mark` (==highlight==)
2. **BeautifulSoup4** post-processing:
   - External links: `target="_blank"` + `rel="noopener noreferrer"`
   - Headings: `x-intersect="highlightTocElement(...)"` for Alpine.js TOC scroll tracking
   - Code blocks: `not-prose` class (bypasses TailwindCSS Typography)
   - Images/videos: `loading="lazy"`
3. **micawber** oEmbed: YouTube URLs and other media are converted to inline embeds
4. **bleach** HTML sanitization (allow-list based)
5. TOC extraction via `update_toc()` (strips outer div)

Result: `html_content`, `html_description`, `html_toc` stored in DB.

#### `blog_utils.py` — Utilities

| Function           | Description                                        |
| ------------------ | -------------------------------------------------- |
| `get_slug()`       | Regex-based title → slug                           |
| `calc_read_mins()` | 200 WPM + 5s/image + 8s/code block                 |
| `strip_markdown()` | Strip Markdown syntax (used for meta descriptions) |

### User Services (`app/services/users/user_handler.py`)

**Pydantic I/O models:**

- `SaveUserInput` — username, full_name, email, timezone, is_active, avatar_location, avatar_upload (UploadFile), password, google_oauth_id, github_oauth_id, role
- `SaveUserResponse` — mirrors SaveBlogResponse pattern

**Key functions:**

| Function                  | Description                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------- |
| `register_user()`         | bcrypt-hash password, INSERT; handles `IntegrityError` for duplicate username/email |
| `update_user()`           | Same; re-hashes password only if a new one is provided                              |
| `send_pw_reset_email()`   | Creates token, enqueues email as a FastAPI background task                          |
| `create_pw_reset_token()` | Generates UUID, HMAC-SHA256 hashes it, stores in `PasswordResetToken`               |

**Password reset flow:**

1. User submits email → `send_pw_reset_email()` called
2. UUID token created → hashed with HMAC-SHA256 (`encryption_handler.hash_token()`)
3. Hashed value stored in `PasswordResetToken.encrypted_query`
4. Raw UUID sent in reset URL email link
5. User clicks link → raw token re-hashed → looked up in DB → verified not expired (15 min TTL)
6. Password updated, token deleted

### Media Services (`app/services/media/media_handler.py`)

Uploads stored under `app/web/html/static/`:

| Destination | Path                    | Content                                                                                 |
| ----------- | ----------------------- | --------------------------------------------------------------------------------------- |
| Avatars     | `static/media/avatars/` | PIL-resized to 600×600, quality 90; SVGs written raw                                    |
| Blog images | `static/media/blog/`    | PIL-resized to max 1200×1200, quality 90; WebP generated; smaller of original/WebP kept |
| Blog videos | `static/media/blog/`    | Raw write                                                                               |

`werkzeug.utils.secure_filename` prevents path traversal. `MediaType` StrEnum: `IMAGE`, `VIDEO`. Multiple `locations` stored as `ARRAY(String)` so both original and WebP can be referenced.

### General Services (`app/services/general/`)

| Module                  | Key exports                                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| `auth_helpers.py`       | `hash_password(pwd) -> str` (bcrypt), `verify_password(plain, hashed) -> bool`                                  |
| `encryption_handler.py` | `hash_token(token) -> str` — HMAC-SHA256 hex digest using `settings.encryption_key` bytes                       |
| `email_handler.py`      | `send_comment_notification_emails()`, `send_pw_reset_email_to_user()` via MailerSend                            |
| `transforms.py`         | `CoercedBool` (truthy string → bool), `CoercedList` (comma-separated → list) — Pydantic `BeforeValidator` types |

---

## 8. HTTP Layer: HTML Sub-App

### Route Modules

All modules in `app/web/html/routes/` are auto-discovered. Each exports `router: APIRouter`.

| Module         | Prefix    | Key routes                                                                                                                                                                       |
| -------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `portfolio.py` | —         | `GET /`, `GET /projects`, `GET /experience`, `GET /healthcheck`                                                                                                                  |
| `blog.py`      | —         | `GET /blog` (list), `GET /blog/{slug}` (read), `GET/POST /blog/create`, `GET/POST /blog/{id}/edit`, `POST /blog/{id}/like`, `POST/PATCH/DELETE /comment/{id}`, series management |
| `auth.py`      | `/auth`   | `POST /auth/token` (set cookie), `GET /auth/refresh-token-cookie`                                                                                                                |
| `users.py`     | —         | `GET/POST /login`, `GET /logout`, `GET/POST /register`, `GET/POST /settings`, `GET/POST /reset-password/{query}`, `GET/POST /request-password-reset`                             |
| `projects.py`  | —         | `GET /twisted-towers`, `GET /moth-hunt`, `GET /file-renamer`                                                                                                                     |
| `games.py`     | —         | `GET /connect-4`                                                                                                                                                                 |
| `errors.py`    | `/errors` | `GET /errors` (general error display)                                                                                                                                            |
| `sitemap.py`   | —         | `GET /sitemap.xml`                                                                                                                                                               |

### Route Handler Pattern

Every HTML route handler:

1. Accepts `request: Request`, optionally `LoggedInUser` / `LoggedInUserOptional` (FastAPI `Depends`), optionally `DBSession`
2. Validates forms with WTForms (`Form.load(await request.form())`)
3. Calls service functions for business logic
4. Returns `templates.TemplateResponse(request, template_path, context_dict)`

For HTMX partial requests, handlers check `request.headers.get("hx-target")` to decide whether to return a full page or a fragment template.

### WTForms Integration

**`app/web/html/wtform_utils/`** provides:

- `Form.load(data)` — converts `dict` or FastAPI `FormData` to `werkzeug.MultiDict` for WTForms
- Custom `BooleanField` — handles string `"true"`/`"false"` from HTMX (not just checkbox `"on"`)
- Form field partials in `shared/partials/forms/`:
  - `field.html` — generic input/select
  - `password_field.html` — Alpine.js show/hide toggle
  - `toggle_field.html` — Alpine.js toggle switch backed by hidden input
  - `markdown_textarea.html` — textarea with markdown toolbar + `TextAreaHistoryManager`
  - `field_errors.html`, `top_error.html`, `submit_button.html`, `hidden_field.html`

**Submission flow:**

1. Template renders `<form hx-post="...">` or `<form method="POST">`
2. Route awaits `request.form()`, calls `Form.load()`, validates
3. Validation failure: re-renders template with form (with errors) at status 422
4. Success: executes business logic, then redirects or returns HTMX fragment

### Template System

Jinja2 templates with `jinja-partials` for explicit sub-template context passing. The `templates` singleton is `Jinja2Templates(directory=TEMPLATES_DIR)` with `jinja_partials` registered.

**Custom Jinja2 globals** (registered in `jinja_globals.py`):

| Global                 | Purpose                                 |
| ---------------------- | --------------------------------------- |
| `abs`, `hasattr`       | Python built-ins in templates           |
| `shorten`              | Text truncation                         |
| `strip_markdown`       | Strip Markdown for meta descriptions    |
| `get_flashed_messages` | Reads and clears session flash messages |
| `sentry_cdn`           | Sentry SDK CDN URL                      |

**Template directory structure:**

```txt
templates/
├── shared/
│   ├── base.html                  # Root layout (Alpine.js root, HTMX globals, nonce)
│   └── partials/
│       ├── head.html              # <head> (CSS, JS, meta, HTMX config)
│       ├── navbar.html            # Responsive nav (scroll-aware, mobile menu)
│       ├── footer.html            # Footer
│       ├── flash_messages.html    # pushNotify() calls for session messages
│       ├── refresh_access.html    # HTMX token refresh every 5 min
│       ├── forms/                 # WTForms field partials
│       └── icons/                 # SVG icon partials
├── blog/
│   ├── list_posts.html            # Blog listing page
│   ├── read_post.html             # Individual post (TOC, comments, likes)
│   ├── edit_post.html             # Admin post editor
│   ├── manage_series.html         # Admin series manager
│   └── partials/                  # HTMX-swappable fragments
├── main/                          # About, projects, experience pages
├── projects/                      # Mini-project pages (Connect 4, etc.)
├── users/                         # Login, register, settings, password reset
└── errors/
    └── general_error.html
```

**`base.html` layout:**

```html
<html
  x-data="{darkMode: $persist(...), smoothScroll: true, loginModalOpen: false}"
  :class="{'dark': darkMode}"
  hx-ext="response-targets, alpine-morph"
>
  <head>
    <!-- head.html partial -->
  </head>
  <body hx-target-error="body" hx-swap="outerHTML">
    <!-- refresh_access.html -->
    <!-- navbar.html -->
    <!-- flash_messages.html -->
    <main hx-boost="true">{% block content %}{% endblock %}</main>
    <!-- footer.html -->
    <!-- script_end.js -->
  </body>
</html>
```

---

## 9. HTTP Layer: REST API Sub-App

### Routes (`/api/v1`)

| Method + Path               | Auth                             | Description                                                                         |
| --------------------------- | -------------------------------- | ----------------------------------------------------------------------------------- |
| `POST /auth/token`          | None                             | Form: `username`+`password` → `Token{access_token, token_type}` (bearer, no cookie) |
| `GET /users`                | `TokenRequiredUser`              | Admin → all users; User → only self                                                 |
| `GET /users/current-user`   | `TokenRequiredUser`              | Current user's data                                                                 |
| `GET /users/{user_id}`      | `TokenRequiredUser`              | User by id                                                                          |
| `POST /users`               | `TokenRequiredUser` (admin only) | Create user → HTTP 201                                                              |
| `PATCH /users/current-user` | `TokenRequiredUser`              | Partial update of self                                                              |

### API Models

| Model            | Fields                                                                                             |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| `ErrorOut`       | `detail: str \| None`                                                                              |
| `UserInPost`     | username (min 3), email (EmailStr), full_name (min 3), password (min 8), avatar_location, timezone |
| `UserInPatch`    | Same, all Optional                                                                                 |
| `UserOutLimited` | id, username, email, full_name, timezone, avatar_location, role, is_active                         |
| `Token`          | access_token, token_type                                                                           |

All `AppError` exceptions → `JSONResponse(status_code=..., content={"detail": ...})`.

---

## 10. Authentication & Authorization

### Dual-Mode Auth

The app supports two authentication modes used in different contexts:

| Mode          | Cookie `access_token`                 | Bearer token                           |
| ------------- | ------------------------------------- | -------------------------------------- |
| Used by       | HTML sub-app (browser)                | REST API (programmatic clients)        |
| Token storage | HttpOnly, Secure, SameSite=lax cookie | `Authorization: Bearer <token>` header |
| JS accessible | No                                    | N/A                                    |

### JWT Tokens

- **Algorithm**: HS256, signed with `settings.jwt_secret`
- **Payload**: `{sub: username, user_id: int, role: Role, exp: datetime}`
- **Lifetime**: 30 minutes (configurable via `settings.jwt_expires_mins`)
- **Refresh**: Only reissued when remaining time falls below a threshold (prevents token churn)

### FastAPI Auth Dependencies (exported from `app/web/auth.py`)

| Dependency             | Type                          | Used in                                                        |
| ---------------------- | ----------------------------- | -------------------------------------------------------------- |
| `LoggedInUser`         | `db_models.User`              | HTML routes requiring login (raises 401 if absent)             |
| `LoggedInUserOptional` | `User \| UnauthenticatedUser` | HTML routes with optional auth; also assigns `guest_id` cookie |
| `TokenRequiredUser`    | `db_models.User`              | API routes requiring bearer token                              |
| `TokenOptionalUser`    | `User \| UnauthenticatedUser` | API routes with optional token                                 |

`LoggedInUserOptional` sets a `guest_id` UUID cookie on unauthenticated users for comment identity tracking.

### Roles & Permissions (`app/permissions.py`)

**`Role`** StrEnum (ordered): `UNAUTHENTICATED` → `USER` → `REVIEWER` → `ADMIN`

**`Action`** StrEnum:

- `EDIT_BP` — allowed: `{ADMIN}`
- `READ_UNPUBLISHED_BP` — allowed: `{REVIEWER, ADMIN}`

```python
# Used as a decorator on route functions:
@requires_permission(Action.EDIT_BP)
async def create_blog_post(current_user: LoggedInUser, **kwargs): ...
```

The decorator checks `current_user.has_permission(action)` and raises `UserPermissionsError` (403) if denied. It preserves the original function signature for FastAPI introspection.

### `AuthUserMixin` (`app/mixins.py`)

Shared by `db_models.User` and `web_models.UnauthenticatedUser`:

- `role: Role`
- `is_authenticated: bool = True`
- `guest_id: str = ""`
- `is_admin` property
- `has_permission(action) -> bool`

`UnauthenticatedUser` (in `web_models.py`): `role=UNAUTHENTICATED`, `is_authenticated=False`, `id=-1`.

### Token Refresh Mechanism

Every HTML page includes the `refresh_access.html` partial:

```html
<div
  hx-get="/auth/refresh-token-cookie"
  hx-trigger="load, every 5m"
  hx-swap="none"
></div>
```

The server renews the cookie if the token is still valid, or deletes the cookie silently if expired. This keeps sessions alive on active pages without user interaction.

---

## 11. Front-End System

### Alpine.js

Alpine.js provides declarative client-side reactivity directly in HTML markup without a build step.

**Global scope** (set on `<html>` in `base.html`):

- `darkMode: $persist(...)` — persisted to `localStorage._x_darkMode`; controls `.dark` class on `<html>` for Tailwind dark mode
- `smoothScroll` — CSS scroll behavior toggle
- `loginModalOpen: false` — any template can open the login modal with `@click="loginModalOpen = true"`

**FOUC prevention**: An inline script in `head.html` reads `localStorage._x_darkMode` and manually applies `.dark` to `<html>` before Alpine initializes, preventing a flash of light-mode content.

**Key Alpine.js usages across templates:**

| Template                                | `x-data` / behavior                                                                        |
| --------------------------------------- | ------------------------------------------------------------------------------------------ |
| `navbar.html`                           | `mobileNavOpen`, `showNav`, `lastScroll`, `navAtTop`; scroll-aware hide/show + mobile menu |
| `blog/list_posts.html`                  | `compact: $persist(...)` — persisted compact/expanded post list view                       |
| `blog/edit_post.html`                   | `isDirty` — `beforeunload` prompt on unsaved changes                                       |
| `blog/read_post.html`                   | `x-intersect` on headings — TOC highlight tracking                                         |
| `users/login_modal.html`                | `x-show="loginModalOpen"`, `x-trap.inert` — modal + focus trap                             |
| `partials/forms/password_field.html`    | `passwordVisible` — show/hide password toggle                                              |
| `partials/forms/toggle_field.html`      | `value` — controlled toggle switch bound to hidden input                                   |
| `partials/forms/markdown_textarea.html` | `historyManager` (`TextAreaHistoryManager`) — undo/redo                                    |
| `footer.html`                           | `year: new Date().getFullYear()` — dynamic copyright year                                  |

**Plugins in use:** `$persist`, `x-trap` (focus plugin), `x-intersect` (intersect plugin), `x-morph` / alpine-morph (morph plugin).

### HTMX

HTMX upgrades standard HTML hyperlinks and forms to AJAX requests without writing JavaScript.

**Global configuration** (inline script in `head.html`):

```js
htmx.config.defaultSettleDelay = 0
htmx.config.scrollBehavior = "auto"
htmx.config.useTemplateFragments = true
```

**Extensions** (on `<html>`): `hx-ext="response-targets, alpine-morph"`:

- `response-targets` — enables `hx-target-4*`, `hx-target-error` for status-code-based targeting
- `alpine-morph` — intelligent DOM diff that preserves Alpine.js state during swaps

**`hx-boost`** on `<main>` upgrades all `<a>` and `<form>` elements to HTMX AJAX navigation (SPA-like experience). Disabled on the blog editor.

**Key HTMX patterns:**

| Pattern          | How                                                                                 |
| ---------------- | ----------------------------------------------------------------------------------- |
| Blog search      | `hx-post` with `hx-swap="morph swap:500ms"` targets `#blog-post-list`               |
| Pagination       | `hx-get` with `hx-push-url="true"` updates URL without full reload                  |
| Like button      | `hx-post` replaces `#like-block` `outerHTML`                                        |
| Comment form     | `hx-post` replaces `#comments-section` `outerHTML`                                  |
| Comment preview  | `hx-post` with delay targets `#base-preview-comment` (live Markdown preview)        |
| Login modal      | `hx-post` targets `#swap-success` on success, `hx-target-4*="#login-form"` on error |
| Token refresh    | `hx-get` with `hx-trigger="load, every 5m"`                                         |
| Delete confirms  | `addConfirmEventListener()` intercepts `htmx:confirm` → SweetAlert2 modal           |
| Fade transitions | `.htmx-fade-out-150ms` / `.htmx-fade-in-300ms` CSS keyframe classes                 |

**CSP nonce propagation**: Inline scripts in HTMX swap responses need a nonce. A script at the bottom of `<body>` sets `htmx.config.inlineScriptNonce = "{{ request.state.nonce }}"` once per page load.

### JavaScript Files

| File                                | Load order              | Contents                                                                               |
| ----------------------------------- | ----------------------- | -------------------------------------------------------------------------------------- |
| `libraries/bundled-non-deferred.js` | Synchronous in `<head>` | Popper.js, Tippy.js, SweetAlert2, HTMX 1.9.12 + extensions, Simple-Notify, Freezeframe |
| `libraries/bundled-deferred.js`     | `defer` in `<head>`     | Alpine.js plugins (focus, intersect, morph, persist) + Alpine.js core                  |
| `custom/script.js`                  | In `<head>`             | Global utilities (see below)                                                           |
| `custom/script_end.js`              | Bottom of `<body>`      | Initializes Tippy tooltips, calls `setAllMediaWidthHeight()`                           |
| `custom/connect4.js`                | Page-specific           | Full Connect 4 game logic (minimax AI, board, game state)                              |

**Global utility functions** (from `script.js`):

| Function                                 | Purpose                                                |
| ---------------------------------------- | ------------------------------------------------------ |
| `pushNotify(title, text, type, timeout)` | Simple-Notify toast notification                       |
| `copyTextToClipboard(text)`              | Copy text to clipboard                                 |
| `setAllMediaWidthHeight()`               | Fix media element dimensions                           |
| `lazyLoadVideos()`                       | Initialize IntersectionObserver for video lazy loading |
| `addFreezeFrame()`                       | Initialize Freezeframe on GIFs                         |
| `highlightTocElement(id)`                | Update active TOC entry (called from `x-intersect`)    |
| `addConfirmEventListener()`              | HTMX confirm interceptor → SweetAlert2                 |
| `setAvatarImage(input)`                  | Preview avatar image on file select                    |
| `setThumbnailImage(input)`               | Preview thumbnail on file select                       |
| `mdTextareaKeyPress(e)`                  | Markdown keyboard shortcuts (bold, italic, etc.)       |
| `promptForExit()`                        | `beforeunload` handler for unsaved changes             |
| `TextAreaHistoryManager`                 | Undo/redo class used by Alpine.js in markdown editor   |

### TailwindCSS

**v4 CSS-first configuration** in `app/web/html/input.css`. Built by `@tailwindcss/cli` to `static/css/tailwind-styles.css`. Minified for production.

**Dark mode**: class-based variant `@custom-variant dark (&:where(.dark, .dark *))` — toggled by Alpine.js on `<html>`.

**Plugins**: `@tailwindcss/typography` (blog prose), `@tailwindcss/forms`, `@tailwindcss/container-queries`.

**Custom theme**: Roboto font; primary (emerald), offset (violet), grayscale (warm), third (yellow) color palettes; responsive breakpoints xs→2xl.

**Custom component classes**: `.section-container`, `.btn`, `.btn-filled`, `.btn-outline`, `.btn-filled-danger`, `.link`, `.blog-prose`, `.blog-nav-highlight`, `.tippy-box`.

---

## 12. Static Assets & Build Pipeline

### Asset Files

```text
static/
├── css/
│   ├── tailwind-styles.css          # Built by TailwindCSS CLI
│   ├── blog-code-hilights.css       # Pygments syntax highlighting
│   ├── connect4.css                 # Connect 4 game board
│   └── libraries/
│       └── bundled.css              # Tippy + Simple-Notify CSS
├── js/
│   ├── custom/
│   │   ├── script.js
│   │   ├── script_end.js
│   │   └── connect4.js
│   └── libraries/
│       ├── bundled-non-deferred.js  # HTMX + tooltips + modals (synchronous)
│       └── bundled-deferred.js      # Alpine.js + plugins (deferred)
└── media/
    ├── avatars/                     # User-uploaded avatars
    └── blog/                        # Blog post images and videos
```

### Cache Busting

Content-hash-based versioning via `scripts/static_version_updater.py`. Three SHA-256 hashes (truncated to 8 chars) are stored as Jinja2 variables in `base.html`:

```html
{% set libraries_static_version = 'e454b3c1' %} {% set custom_static_version =
'56505df6' %} {% set tailwind_static_version = '254b2dde' %}
```

Assets are referenced as `url_for('html:static', path='...')?{{ version }}`. Caddy sets `max-age=31536000, immutable` for CSS/JS/image files.

### Third-Party Bundling

`scripts/bundler.py` fetches library files from jsDelivr/unpkg, optionally minifies (Toptal API), and concatenates into bundle files. HTMX is pinned to 1.9.12 (the `response-targets` extension is broken in HTMX ≥ 2).

### Development vs Production Serving

- **Development**: uvicorn serves `/static` directly via `StaticFiles`
- **Production**: Caddy serves `/static/*` from a shared Docker volume (`./app/web/html/static:/static`), bypassing FastAPI entirely for improved performance and caching

---

## 13. Error Handling

### Domain Exceptions (`app/errors.py`)

All exceptions inherit from `AppError` (HTTP-agnostic class-level, but carry `status_code` for convenience):

| Exception                         | Status |
| --------------------------------- | ------ |
| `AppError`                        | 500    |
| `UserNotFoundError`               | 404    |
| `BlogPostNotFoundError`           | 404    |
| `BlogPostCommentNotFoundError`    | 404    |
| `BlogPostMediaNotFoundError`      | 404    |
| `BlogPostSeriesNotFoundError`     | 404    |
| `PasswordResetTokenNotFoundError` | 404    |
| `PasswordResetTokenExpiredError`  | 400    |
| `UserNotAuthenticatedError`       | 401    |
| `UserNotValidatedError`           | 401    |
| `UserPermissionsError`            | 403    |
| `UserAlreadyExistsError`          | 409    |

### HTML Error Handling (`app/web/html/error_handlers.py`)

Registered by `register_error_handlers(app)`:

| Error                       | Behavior                                              |
| --------------------------- | ----------------------------------------------------- |
| `LoginExpiredError`         | Delete cookie, flash warning, redirect to current URL |
| `UserNotAuthenticatedError` | Flash error, redirect to `/login?next=<current_url>`  |
| `AppError` (generic)        | Redirect to `/errors?detail=...&status_code=...`      |
| `RequestValidationError`    | Log error, redirect to `/errors` with generic message |

The `/errors` route renders `errors/general_error.html`.

### HTMX Error Targets

Default on `<body>`:

```html
hx-target-error="body" hx-swap="outerHTML"
```

Unhandled HTMX errors replace the full page. Individual HTMX requests can override with `hx-target-error="#element"` to swap only a specific section.

### API Error Handling (`app/web/api/error_handlers.py`)

```python
JSONResponse(status_code=error.status_code, content={"detail": error.detail})
```

---

## 14. Flash Messaging

Flash messages are stored in the Starlette session (under `_messages`) and consumed once on the next rendered page.

**`FlashMessage` model fields:** `title`, `text`, `category` (error/success/info/warning), `timeout` (seconds, default 5).

**Delivery pipeline:**

1. Route calls `FlashMessage.flash(request)` → writes to `request.session["_messages"]`
2. Next request: `base.html` includes `flash_messages.html`
3. Partial calls `get_flashed_messages(request)` (Jinja2 global) → reads and clears messages
4. Partial generates an inline `<script>` calling `pushNotify(title, text, type, timeout)` for each message
5. `pushNotify()` (from `script.js`) uses Simple-Notify to display a toast

Notifications appear at right-bottom on desktop, top-center on mobile (≤ 768px).

---

## 15. Blog System: End-to-End

### Reading a Blog Post

1. Browser requests `GET /blog/my-post-slug`
2. Caddy proxies to FastAPI
3. `CSPMiddleware` generates nonce
4. Route handler (`blog.py`) extracts slug, calls `blog_handler.get_bp_from_slug(db, slug)`
5. If not found by slug, tries `OldBlogPostSlug` history (old slug → current post)
6. If `is_published=False` and user lacks `READ_UNPUBLISHED_BP` permission → 404
7. `TemplateResponse` renders `blog/read_post.html` with post data
8. Template outputs `{{ blog_post.html_content|safe }}` — pre-rendered HTML from DB
9. `blog-code-hilights.css` provides syntax highlighting
10. `x-intersect` on headings drives TOC highlight as user scrolls
11. HTMX like button, comment form, and comment editing work as partial swaps

### Creating / Editing a Blog Post (Admin)

1. Admin user navigates to `/blog/create` or `/blog/{id}/edit`
2. Route checks `@requires_permission(Action.EDIT_BP)` — must be ADMIN
3. Large WTForms form with markdown editor (`markdown_textarea.html` partial)
4. `hx-boost` disabled on this page (prevents state loss in editor)
5. `isDirty` Alpine.js flag triggers `beforeunload` if leaving with unsaved changes
6. Live preview: HTMX `hx-post` to `/blog/preview` renders markdown fragment
7. On save: form POST → `blog_handler.save_blog_post(db, SaveBlogInput(...))` → markdown rendered → stored in DB
8. Old slug preserved in `OldBlogPostSlug` if slug changed
9. Flash message on success

### Blog Listing & Search

1. Browser requests `GET /blog?search=python&tags=tutorial&order=newest&page=2`
2. Route calls `blog_handler.get_blog_posts(db, search=..., tags=..., order_by=..., page=..., results_per_page=...)`
3. Single SQL query with `COUNT(*) OVER()` window function returns posts + total count
4. `Paginator` object passed to template
5. HTMX search: form submits `hx-post` → route returns `blog/partials/listed_posts.html` fragment → swapped with `morph swap:500ms` to preserve Alpine state
6. HTMX pagination: links use `hx-push-url="true"` to update browser URL

### Comments

1. Unauthenticated users: `guest_id` UUID cookie identifies commenter
2. Authenticated users: `user_id` links to `User`
3. `md_content` stored; converted to `html_content` on save via `markdown_parser`
4. `hx-post` to `/blog/{id}/comment` → returns updated `comments.html` fragment
5. Comment preview: `hx-post` to `/blog/preview-comment` with 300ms delay
6. Admin can edit/delete any comment; user can edit/delete their own
7. New comment triggers `send_comment_notification_emails()` as a background task

---

## 16. User System: End-to-End

### Registration

1. `GET/POST /register` → `users/register.html` + `register_form.html` partial
2. WTForms `RegisterForm` validates username/email/password
3. `user_handler.register_user(db, SaveUserInput(...))` → bcrypt hash → DB insert
4. `IntegrityError` on duplicate username/email → field-level error display
5. Flash success → redirect to login

### Login

**Full page login:**

1. `GET /login` → `users/login.html`
2. POST → `auth_handler.authenticate_user(db, username, password)` → `verify_password()`
3. On success: `create_access_token()` → set `access_token` HttpOnly cookie → redirect

**Login modal (any page):**

1. Any template: `<button @click="loginModalOpen = true">`
2. `users/login_modal.html` (included in `base.html`): `x-show="loginModalOpen"`, `x-trap.inert`
3. Form uses `hx-post="/login"`:
   - 200: swaps `#swap-success` → triggers redirect via inline script
   - 4xx: `hx-target-4*="#login-form"` swaps error state back into modal

### Password Reset

1. `GET /request-password-reset` → form for email submission
2. POST → `user_handler.send_pw_reset_email(db, email, background_tasks)`
3. Background task: `email_handler.send_pw_reset_email_to_user(user, query)` via MailerSend
4. Email contains link: `/reset-password/{raw_uuid}`
5. `GET /reset-password/{query}` → form for new password
6. POST: raw token HMAC-SHA256 hashed → looked up in DB → checked not expired (15 min)
7. Password updated → token deleted → flash + redirect to login

### Settings / Profile

- `GET/POST /settings` → `users/settings.html`
- WTForms `SettingsForm`
- Avatar upload: multipart POST → `media_handler.upload_avatar()` (PIL resize 600×600) → path stored in User

---

## 17. Media System: End-to-End

### Avatar Upload

1. Settings form: `<input type="file" name="avatar_upload">` multipart
2. Route passes `UploadFile` to `SaveUserInput.avatar_upload`
3. `media_handler.upload_avatar(pic, name=f"{user.id}_{uuid4()}")`
4. Pillow resizes to 600×600, saves as JPEG quality 90; SVGs written raw
5. `User.avatar_location` updated with relative path from `static/`
6. Old avatar file deleted from disk if path changed

### Blog Media Upload

1. Admin editor: `edit_post_media_form.html` → multipart POST to `/blog/{id}/media`
2. Route receives `UploadFile`, determines type (image vs video)
3. `media_handler.upload_blog_media(file, name, media_type)`
4. Images: Pillow resize to 1200×1200 max; WebP variant generated; smaller kept
5. Videos: raw write
6. `BlogPostMedia` record created with `locations: ARRAY(String)` (original + WebP paths)
7. Media referenced in Markdown content via URL paths; `<source srcset>` can reference multiple locations

---

## 18. Security Model

### Authentication Security

| Mechanism             | Implementation                                                             |
| --------------------- | -------------------------------------------------------------------------- |
| Password hashing      | bcrypt (passlib), slow KDF                                                 |
| JWT signing           | HS256, `settings.jwt_secret`                                               |
| Token storage         | HttpOnly + Secure + SameSite=lax cookie (inaccessible to JS)               |
| CSRF protection       | SameSite=lax on session + JWT cookies (no separate CSRF token needed)      |
| Password reset tokens | UUID (128-bit entropy) → HMAC-SHA256 → stored hash; raw token never stored |
| Session cookies       | Signed via itsdangerous, `settings.session_secret`                         |

### Content Security Policy

Per-request nonce (`base64(secrets.token_bytes(16))`) generated by `CSPMiddleware` and injected into `request.state.nonce`. All inline `<script>` tags use `nonce="{{ request.state.nonce }}"`.

| CSP directive | Allowed sources                                                       |
| ------------- | --------------------------------------------------------------------- |
| `default-src` | `'self'`                                                              |
| `script-src`  | `'self'`, `'nonce-{nonce}'`, `'unsafe-eval'` (Alpine.js), Sentry CDNs |
| `style-src`   | `'self'`, fonts.bunny.net, `'unsafe-inline'`                          |
| `font-src`    | `'self'`, fonts.bunny.net                                             |
| `frame-src`   | YouTube, Scratch                                                      |
| `connect-src` | `'self'`, Sentry ingest                                               |
| `worker-src`  | `'self'`, Sentry CDNs, `blob:`                                        |
| `img-src`     | `*`, `data:`, `blob:`                                                 |
| `media-src`   | `'self'`, `data:`, `blob:`                                            |
| `object-src`  | `'none'`                                                              |
| `form-action` | `'self'`                                                              |

### Input Security

- WTForms validates all HTML form input before processing
- Pydantic v2 validates all service-layer inputs
- bleach sanitizes Markdown-generated HTML (allow-list)
- `werkzeug.utils.secure_filename` prevents path traversal in file uploads
- SQLAlchemy ORM prevents SQL injection
- `@requires_permission` decorator enforces authorization on all admin routes

---

## 19. Monitoring

**Sentry SDK** initialized in `app/web/monitoring.py`:

- DSN, environment, and per-environment sample rates from `settings`
- `StarletteIntegration(transaction_style="endpoint")`
- `FastApiIntegration(transaction_style="endpoint")`
- `enable_tracing=True`
- Browser-side session replay via `settings.sentry_cdn` (JS SDK loaded from CDN)
- Sentry ingest URL injected into CSP `connect-src`

---

## 20. Containerization & Deployment

### Docker

**Dockerfile** (`docker_config/Dockerfile.app`) — multi-stage build:

1. **Build stage** (`python:3.14-slim`): `uv` installs dependencies into `/opt/venv` from `requirements-prod.txt`; `UV_COMPILE_BYTECODE=1`
2. **Final stage** (`python:3.14-slim`): copies venv + app code; runs as `codewithteddy` user (UID 1001)

**docker-compose services:**

| Service               | Role                | Key detail                                                              |
| --------------------- | ------------------- | ----------------------------------------------------------------------- |
| `app` (`web_app`)     | FastAPI application | Port 8000 (internal); `DB_CREATE_TABLES=0`; healthcheck `/healthcheck`  |
| `migration`           | Alembic runner      | Same image; `python -m scripts.alembic upgrade`; exits after completion |
| `db`                  | PostgreSQL 16.2     | Persistent volume; `pg_isready` healthcheck                             |
| `caddy-dev` / `caddy` | Reverse proxy       | Ports 80/443; dev vs prod Caddyfile                                     |

Secrets injected via Docker secrets into `/run/secrets/`. Static files shared as a Docker volume between `app` and `caddy`.

### Caddy (Production)

- HTTP/2 + HTTP/3 (h1, h2, h3)
- Domain canonicalization: `www.codewithteddy.dev` → `codewithteddy.dev` (301), `*.codewithteddy.com` → `codewithteddy.dev` (301)
- Compression: gzip level 6, zstd
- **Static files** (`/static/*`): served from volume; cache headers: CSS/JS/images → `immutable, max-age=31536000`; media files → `max-age=86400`
- **Dynamic requests**: reverse proxy → `web_app:8000`; health check every 30s; timeouts configured; `round_robin` ready for horizontal scaling
- **Security**: removes `Server` header; CSP delegated to FastAPI for nonce support

### Deploy Script (`scripts/deploy.sh`)

Flags: `--dev/--prod`, `--from-scratch`, `--down`, `--skip-build`, `--if-needed`.

Production flow: fetch latest release branch → build Docker images → stop old containers → start new → prune dangling images. Logs to date-stamped files in `logs/`.

---

## 21. Database Migrations

Alembic manages schema evolution. `migrations/env.py` reads `settings.db_connection_string` and uses `db_models.Base.metadata` for autogenerate.

**CLI wrapper** (`scripts/alembic.py`):

```bash
python -m scripts.alembic migrate -m "description"   # autogenerate
python -m scripts.alembic upgrade [revision]          # upgrade (default: head)
python -m scripts.alembic downgrade [revision]        # downgrade (default: -1)
```

**Migration history:**

| Migration      | Change                                            |
| -------------- | ------------------------------------------------- |
| `de229330a488` | Initial full schema                               |
| `9477169e5ea8` | `BlogPostMedia.locations`: String → ARRAY(String) |
| `45dfd4469e80` | Add `PasswordResetToken` table                    |

In Docker, the `migration` service runs `alembic upgrade head` before `app` starts. `db_create_tables=False` in Docker so SQLAlchemy never auto-creates tables.

---

## 22. Developer Tooling & Testing

### Local Development

```bash
# Start local Postgres + seed dummy data
python -m scripts.start_local_postgres --migrate head

# Start app (tmux: Tailwind watcher + uvicorn hot-reload)
./scripts/run-dev.sh
```

`scripts/start_local_postgres.py` uses the Docker Python SDK to spin up a `postgres` container on port 5432, wait for health, optionally run migrations and seed with Faker-generated dummy data.

### Tests

```bash
pytest                          # unit + functional (default, fast)
pytest --integration=local      # + integration tests against local env
pytest --playwright=local       # + Playwright E2E tests
pytest --all                    # everything
```

**Test infrastructure:**

- Separate `postgres_test` container on port 5433; created and destroyed per session
- `CustomTestClient(TestClient)` — wraps all HTTP methods with optional `to_file=True` debug flag
- Pre-generated auth tokens: `ADMIN_COOKIE`, `BASIC_COOKIE`, `ADMIN_TOKEN`, `BASIC_TOKEN`
- `anyio_backend = "asyncio"` for async tests
- `DeprecationWarning`s from app/test/script code are errors

**Test types:**

| Type           | Location                   | Description                             |
| -------------- | -------------------------- | --------------------------------------- |
| Unit           | `tests/unit_tests/`        | Service layer functions, no HTTP        |
| Functional     | `tests/functional_tests/`  | Full request/response with `TestClient` |
| Integration    | `tests/integration_tests/` | Against live local or prod environment  |
| Playwright E2E | `tests/playwright_tests/`  | Real browser automation                 |

### Code Quality

```bash
pre-commit run --all-files   # runs Ruff + ty + other hooks
```

- **Ruff**: linter + formatter, 100-char line length, in `ruff.toml`
- **ty**: Astral type checker (successor to mypy); all functions require return type annotations
- **pre-commit**: enforces both on every commit

---

## 23. Full Request Lifecycle

### Example: Authenticated user views a blog post

```txt
1. Browser: GET https://codewithteddy.dev/blog/my-post-slug
   Cookie: access_token=<jwt>; guest_id=<uuid>

2. Caddy:
   - TLS termination
   - Check /static/* → not matched
   - Reverse proxy to web_app:8000

3. FastAPI root app:
   - SessionMiddleware: loads session from signed cookie
   - CORSMiddleware: not a cross-origin request, no-op

4. HTML sub-app:
   - CSPMiddleware: generates nonce, attaches to request.state.nonce

5. Route matching: GET /blog/{slug} → blog.py handler

6. FastAPI dependency injection:
   - LoggedInUserOptional:
     - Reads access_token cookie
     - Calls parse_access_token() → jwt.decode() → {user_id: 42, role: "user"}
     - Queries DB: SELECT * FROM users WHERE id=42
     - Returns User ORM object
   - DBSession: yields AsyncSession

7. @requires_permission check: not required for reading published posts

8. Business logic:
   - blog_handler.get_bp_from_slug(db, "my-post-slug")
   - Executes: SELECT blog_posts ... WHERE slug='my-post-slug' [+ selectinloads]
   - If is_published=False: checks user.has_permission(READ_UNPUBLISHED_BP) → 404 if denied
   - Returns BlogPost ORM object with tags, media, comments, series loaded

9. Template rendering:
   - templates.TemplateResponse(request, "blog/read_post.html", {
       "blog_post": blog_post,
       "current_user": user,
       "request": request,
   })
   - Jinja2 renders:
     - base.html (Alpine root, HTMX extensions, nonce in script tags)
     - head.html (CSS + JS bundles with version hashes)
     - navbar.html
     - flash_messages.html (reads + clears session messages)
     - blog/read_post.html:
       - {{ blog_post.html_content|safe }} (pre-rendered HTML from DB)
       - html_toc rendered in sidebar
       - comment section, like button

10. Response: 200 HTML
    Set-Cookie: access_token=<refreshed_jwt>; HttpOnly; Secure; SameSite=lax
    Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-abc123' ...

11. Browser:
    - Parses HTML
    - Loads JS bundles (HTMX sync, Alpine.js deferred)
    - HTMX: hx-trigger="load" on hidden div → GET /auth/refresh-token-cookie (no-op if fresh)
    - Alpine.js initializes: darkMode applied, navbar scroll listeners attached
    - x-intersect on headings: TOC highlighting active
    - Freezeframe + lazy video initialized via custom_js_end block
    - Tippy tooltips initialized by script_end.js
```

### Example: HTMX partial request (blog search)

```text
1. User types in search box
2. HTMX: POST /blog (hx-trigger="input delay:500ms")
   hx-target="#blog-post-list", hx-swap="morph swap:500ms"
   Form data: search=python

3. CSPMiddleware: new nonce
4. Route: reads search param, calls blog_handler.get_blog_posts(db, search="python")
5. SQL: SELECT ... WHERE ts_vector @@ to_tsquery('python') [+ COUNT(*) OVER()]
6. Returns Paginator
7. Template: detects HTMX request → renders blog/partials/listed_posts.html fragment
8. Response: 200 HTML fragment
9. HTMX: alpine-morph diffs DOM → preserves compact=true Alpine state
10. URL: unchanged (no hx-push-url on search)
```

---

## 24. Integration Wiring Reference

### Complete Feature → Code Path Table

| Feature          | Front-End                                                        | Back-End                                                       |
| ---------------- | ---------------------------------------------------------------- | -------------------------------------------------------------- |
| Page navigation  | `hx-boost` on `<main>` + standard `<a>`                          | `GET` route → `TemplateResponse`                               |
| Form submission  | `<form method="POST">` or `hx-post`                              | `await request.form()` → `Form.load()` → WTForms validate      |
| Auth cookie      | HttpOnly cookie, never JS-visible                                | JWT in `access_token` cookie → decoded by `LoggedInUser` dep   |
| Token refresh    | `hx-trigger="load, every 5m"` → `GET /auth/refresh-token-cookie` | `refresh_token()` reissues if expiry near                      |
| Partial updates  | `hx-get/post/patch/delete` + `hx-target`                         | Route detects HTMX header → returns fragment template          |
| Flash messages   | `pushNotify()` calls in `flash_messages.html`                    | `FlashMessage.flash(request)` → session `_messages`            |
| Login modal      | Alpine `loginModalOpen`, `x-show`, `x-trap`                      | Same `/login` POST route                                       |
| Dark mode        | Alpine `$persist(darkMode)` → `.dark` on `<html>`                | Tailwind class variant; no server involvement                  |
| URL state        | `hx-push-url="true"` on paginator links                          | Query params read by route handler                             |
| Blog search      | HTMX POST + morph swap                                           | `ts_vector.match()` → GIN index query                          |
| Blog content     | `{{ blog_post.html_content \| safe }}`                           | Markdown → HTML at save time via `markdown_parser.py`          |
| TOC highlight    | `x-intersect` on headings (added by BeautifulSoup)               | `x-intersect` attribute injected during markdown processing    |
| Like button      | `hx-post` replaces `#like-block` outerHTML                       | Route increments `blog_post.likes`, returns `like_button.html` |
| Comments         | HTMX POST/PATCH/DELETE → `#comments-section`                     | `SaveCommentInput` → `save_comment()` → html render            |
| Comment preview  | HTMX POST delay 300ms → `#base-preview-comment`                  | Returns `markdown_parser.markdown_to_html(content)`            |
| Delete confirm   | `addConfirmEventListener()` → SweetAlert2                        | HTMX `hx-confirm` attribute triggers the listener              |
| Media upload     | Multipart form POST                                              | `UploadFile` → Pillow processing → `static/media/`             |
| Avatar preview   | `setAvatarImage(input)` JS function                              | File input `onchange` → FileReader → `<img src>`               |
| CSP nonce        | `nonce="{{ request.state.nonce }}"` on all inline scripts        | `CSPMiddleware` generates per-request nonce                    |
| Error pages      | `hx-target-error="body"` default                                 | `register_error_handlers()` → redirect to `/errors`            |
| Static assets    | `url_for('html:static', path='...')?{{ version }}`               | Content-hash versioning; Caddy 1-year immutable cache          |
| Sitemap          | Linked from `robots.txt`                                         | `aiocache` 1-hour TTL; queries all published posts             |
| Sentry (browser) | Sentry JS SDK from `settings.sentry_cdn`                         | Sentry Python SDK on server via `monitoring.py`                |

### Architecture Diagram

```txt
┌────────────────────────────────────────────────────────────┐
│                          Browser                           │
│  Alpine.js (reactive)  HTMX (AJAX)  TailwindCSS (styles)   │
└──────────────┬───────────────────────────────────┬─────────┘
               │ HTTPS                             │ Cookies
               ▼                                   │
┌────────────────────────────────────────────────────────────┐
│                     Caddy 2.10                             │
│  TLS  |  /static/* → volume  |  rest → web_app:8000        │
└──────────────┬─────────────────────────────────────────────┘
               │
               ▼
┌───────────────────────────────────────────────────────────┐
│              Root FastAPI App (app/web/main.py)           │
│  SessionMiddleware (flash)  |  CORSMiddleware             │
│                                                           │
│  ┌──────────────────┐   ┌──────────────────────────────┐  │
│  │   /api/v1        │   │   / (HTML sub-app)           │  │
│  │  JWT Bearer auth │   │  CSPMiddleware (nonce)       │  │
│  │  /auth/token     │   │  Auto-discovered routes      │  │
│  │  /users/**       │   │  WTForms + Jinja2 templates  │  │
│  └────────┬─────────┘   └────────────┬─────────────────┘  │
└───────────┼─────────────────────────┼─────────────────────┘
            │                         │
            ▼                         ▼
┌────────────────────────────────────────────────────────────┐
│                    Service Layer (app/services/)           │
│  blog_handler  user_handler  media_handler  auth_helpers   │
│  markdown_parser  email_handler  encryption_handler        │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│               Data Access Layer (app/datastore/)           │
│  AsyncEngine  →  AsyncSession  →  SQLAlchemy ORM models    │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│                   PostgreSQL 16.2                          │
│  users  blog_posts  blog_post_comments  blog_post_media    │
│  blog_post_series  blog_post_tags  password_reset_tokens   │
└────────────────────────────────────────────────────────────┘
```
