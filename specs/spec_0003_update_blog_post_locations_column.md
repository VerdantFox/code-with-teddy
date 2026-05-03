# Spec 0003: Update `BlogPostMedia.locations` Column to PostgreSQL Array

**Status:** Complete

---

## Overview

The `BlogPostMedia.locations` column currently stores file paths as a comma-separated string (e.g. `"/media/blog/img.webp,/media/blog/img.png"`), which is a CSV-in-a-column anti-pattern. This spec replaces that column with a PostgreSQL `ARRAY(String)` column so each location is a proper first-class value, eliminating the need for the runtime `locations_to_list()` helper and making the data structure honest.

### Acceptance Criteria

- `BlogPostMedia.locations` is stored in PostgreSQL as an `ARRAY(String)` column (not a `VARCHAR`).
- `BlogPostMedia.locations` is typed as `list[str]` in the SQLAlchemy ORM model.
- The `locations_to_list()` helper method is removed from `BlogPostMedia`.
- All call sites that previously called `locations_to_list()` are updated to access `.locations` directly (already a `list[str]`).
- `media_handler.save_image()` and `save_video()` return `list[str]` instead of a comma-joined string.
- `blog_handler.commit_media_to_db()` accepts `locations: list[str]` (renamed from `locations_str: str`) and stores it correctly.
- `blog_handler.save_media_for_blog_post()` and related call sites pass a `list[str]` where they previously passed a string.
- An Alembic migration migrates existing data from the comma-separated string column to the new array column, with a downgrade path that converts back.
- All existing tests continue to pass after the change.
- Test fixtures that call `commit_media_to_db` pass `list[str]` for the `locations` parameter.

---

## Research

### `BlogPostMedia` ORM Model (`app/datastore/db_models.py`)

`BlogPostMedia` (table `blog_post_media`) has the following relevant columns:

```python
class BlogPostMedia(Base):
    id: Mapped[IntPK]
    blog_post_id: Mapped[BlogPostFK | None]
    blog_post: Mapped[BlogPost] = relationship(back_populates="media")
    name: Mapped[str]
    locations: Mapped[str]  # ← the problem column
    media_type: Mapped[str]
    position: Mapped[int | None]
    created_timestamp: Mapped[DateTimeIndexed]

    def locations_to_list(self) -> list[str]:
        """Get the media locations as a list."""
        return self.locations.split(",")
```

`locations` has no annotated column type override, so SQLAlchemy maps it to a plain `VARCHAR`. The `locations_to_list()` method splits on commas at runtime to reconstruct the list. The docstring on the class mentions "If multiple versions of the file are included, they are comma-separated."

The `BlogPost.media` relationship orders by `(position ASC, created_timestamp ASC)` and uses `selectinload` in `_get_bp_statement()`.

### Media Handler (`app/services/media/media_handler.py`)

`upload_blog_media()` → `save_media()` → `save_image()` or `save_video()`, returning `tuple[str, str]` of `(locations_string, media_type)`.

**`save_image(name, image_file)`** builds the comma-separated string:

- For gif/svg/webp: writes the file as-is and returns a single path string (no comma).
- For other images (png, jpg, etc.): saves the original using Pillow, then converts to webp. If the webp version is smaller, both paths are included: `",".join(get_path_str_from_static(img) for img in (webp_path, og_path))`. If the webp is not smaller, it is deleted and only the original path is returned.
- On `PIL.UnidentifiedImageError`: saves without Pillow, returns single path.

So `save_image` returns a string that is either a single path or exactly two comma-joined paths (`webp_path,original_path`).

**`save_video(name, video)`** saves the file directly and returns a single path string — never multiple paths.

**`del_media_from_path_str(path_str)`** accepts a single path string, not a list, and deletes that file. It is called once per location in a loop by the blog handler's delete function.

### Blog Handler (`app/services/blog/blog_handler.py`)

**`_save_bp_media(name, blog_post_slug, media)`** wraps `media_handler.upload_blog_media()` and returns `tuple[str, str]` — the raw comma-string and media type.

**`save_media_for_blog_post(db, blog_post, media, name)`** calls `_save_bp_media` to get `locations_str, media_type`, then calls `commit_media_to_db()`:

```python
locations_str, media_type = _save_bp_media(
    name=name, blog_post_slug=blog_post.slug, media=media
)
return await commit_media_to_db(
    db=db,
    blog_post=blog_post,
    name=name,
    locations_str=locations_str,
    media_type=media_type,
)
```

**`commit_media_to_db(db, *, blog_post, name, locations_str, media_type, position)`** — the public DB-write function. It creates a `BlogPostMedia` row with `locations=locations_str`. This is also called directly from test fixtures, so any signature change propagates to tests.

**`delete_media_from_blog_post(db, media_id, bp_id)`** uses the helper to iterate:

```python
media_locations = media.locations_to_list()
for location in media_locations:
    media_handler.del_media_from_path_str(location)
```

### Jinja2 Template (`app/web/html/templates/blog/partials/list_post_media.html`)

The template calls `media_item.locations_to_list()` at line 60 to get a local `locations` list:

```jinja
{% set locations = media_item.locations_to_list() %}
{% if media_item.media_type == "image" and locations.__len__() == 1 %}
  <img src="{{ url_for('html:static', path=locations[0]) }}" ... />
{% elif media_item.media_type == "image" %}
  <picture>
    {% for location in locations[:-1] %}<source ... />{% endfor %}
    <img src="{{ url_for('html:static', path=locations[-1]) }}" />
  </picture>
{% elif media_item.media_type == "video" %}
  <video>{% for location in locations %}<source ... />{% endfor %}</video>
{% endif %}
```

After the change, if `locations` is already a `list[str]` on the model, the template can replace `media_item.locations_to_list()` with `media_item.locations` directly. All indexing and iteration will continue to work identically.

### Alembic Migrations

The initial migration (`de229330a488_initial_migration.py`) defines the column as:

```python
sa.Column("locations", sa.String(), nullable=False),
```

A new migration will need to:

1. **Upgrade**: Add a temporary `locations_array` column as `ARRAY(String)`, use a SQL expression to split the existing string values (e.g. `string_to_array(locations, ',')`) to populate it, drop the old `locations` column, rename `locations_array` → `locations`.
2. **Downgrade**: Reverse by adding `locations_str TEXT`, populating it with `array_to_string(locations, ',')`, dropping the array column, and renaming back.

The `migrations/env.py` is standard Alembic; `target_metadata = db_models.Base.metadata` is already set so autogenerate will detect the column type change. However, because the migration involves a non-trivial data transformation (string → array), the autogenerated script must be hand-edited to include the data migration step.

### SQLAlchemy Array Type

PostgreSQL `ARRAY` is supported via `sqlalchemy.dialects.postgresql.ARRAY`. The ORM mapping would change to:

```python
from sqlalchemy.dialects.postgresql import ARRAY

locations: Mapped[list[str]] = mapped_column(ARRAY(String))
```

`ARRAY(String)` stores a native PostgreSQL array. SQLAlchemy reads it back as a Python `list[str]` automatically. No annotated type alias is needed unless arrays become common across models (they don't appear elsewhere in this codebase).

### Test Fixtures and Tests

**`tests/model_fixtures.py`** calls `commit_media_to_db` three times with `locations_str="some_location1.png"` (etc.) — single-path strings. These will need to change to `locations=["some_location1.png"]` after the parameter is renamed.

**`tests/functional_tests/html_tests/blog/test_blog_media.py`** covers:

- Permission enforcement for upload, reorder, and delete (guest/basic/admin)
- Upload of PNG, JPG, SVG, WEBP, GIF, MP4, WEBM — verifying the response text contains the media name
- Reorder (PATCH) with various position values, checking rendered order
- Delete (DELETE) verifying the deleted item no longer appears and others do

None of these tests directly assert on `locations` values or call `locations_to_list()`, so they should pass unchanged after the model is updated. The `find_order` helper searches HTML text for media names, which are unrelated to the `locations` column.

**`tests/unit_tests/services/blog/test_blog_utils.py`** covers `blog_utils` functions and does not touch media handling.

No unit tests exist for `media_handler.save_image()` or `save_video()` directly; they are exercised through the functional upload tests (which mock `BLOG_UPLOAD_FOLDER` to a `tmp_path`).

### Summary of All Touch Points

| Location                                             | Current behaviour                    | Must change                                                  |
| ---------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------ |
| `db_models.BlogPostMedia.locations`                  | `Mapped[str]` (VARCHAR)              | `Mapped[list[str]]` with `ARRAY(String)`                     |
| `db_models.BlogPostMedia.locations_to_list()`        | splits on comma                      | **Remove** method                                            |
| `media_handler.save_image()`                         | returns `str` (comma-joined paths)   | return `list[str]`                                           |
| `media_handler.save_video()`                         | returns `str` (single path)          | return `list[str]`                                           |
| `media_handler.upload_blog_media()` / `save_media()` | returns `tuple[str, str]`            | return `tuple[list[str], str]`                               |
| `blog_handler._save_bp_media()`                      | returns `tuple[str, str]`            | return `tuple[list[str], str]`                               |
| `blog_handler.save_media_for_blog_post()`            | passes `locations_str: str`          | pass `locations: list[str]`                                  |
| `blog_handler.commit_media_to_db()`                  | param `locations_str: str`           | param `locations: list[str]`                                 |
| `blog_handler.delete_media_from_blog_post()`         | calls `locations_to_list()`          | iterate over `.locations` directly                           |
| Template `list_post_media.html` line 60              | `media_item.locations_to_list()`     | `media_item.locations`                                       |
| `tests/model_fixtures.py` (3 calls)                  | `locations_str="some_location1.png"` | `locations=["some_location1.png"]`                           |
| Alembic migration                                    | `sa.String()` for the column         | new migration: `String → ARRAY(String)` with data conversion |

---

## Plan

### Approach

Change the `BlogPostMedia.locations` column from a comma-separated `VARCHAR` to a PostgreSQL native `ARRAY(String)`. The change propagates outward from the ORM model: the media handler functions that build the string become functions that return a list, the blog handler functions that pass and store the string are updated to pass and store a list, and the single template that calls `locations_to_list()` is updated to read `.locations` directly. An Alembic migration handles the data transformation in both directions. No new abstractions are introduced; every change is a straightforward type swap along the existing call chain.

### Files to Modify

| File                                                              | Change                                                                                                                                  |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `app/datastore/db_models.py`                                      | Change `locations` column type to `ARRAY(String)`; update docstring; remove `locations_to_list()`                                       |
| `app/services/media/media_handler.py`                             | Change `save_image()`, `save_video()`, `save_media()`, and `upload_blog_media()` to return `list[str]`                                  |
| `app/services/blog/blog_handler.py`                               | Update `_save_bp_media()`, `save_media_for_blog_post()`, `commit_media_to_db()`, and `delete_media_from_blog_post()` to use `list[str]` |
| `app/web/html/templates/blog/partials/list_post_media.html`       | Replace `media_item.locations_to_list()` with `media_item.locations`                                                                    |
| `tests/model_fixtures.py`                                         | Change three `commit_media_to_db` calls to pass `locations=["some_location1.png"]` etc.                                                 |
| `migrations/versions/<new_revision>_locations_string_to_array.py` | New Alembic migration: `VARCHAR → ARRAY(String)` with data conversion and downgrade                                                     |

### Implementation Details

#### 1. `app/datastore/db_models.py`

Add `ARRAY` to the PostgreSQL dialect import (already imports `TSVECTOR` from that module). Change the `locations` column mapping and update the class docstring to drop the "comma-separated" language. Remove `locations_to_list()` entirely.

```python
# Existing import — add ARRAY:
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR

# ...


class BlogPostMedia(Base):
    """Blog post media model.

    Might include images or videos.

    Attributes
    ----------
        name: The name of the media, given as the title of the HTML tag.
        locations: The locations of the file on the filesystem. If multiple
            versions of the file are included (e.g. webp + original), each
            path is a separate element in the list.

    """

    __tablename__ = "blog_post_media"

    id: Mapped[IntPK]
    blog_post_id: Mapped[BlogPostFK | None]
    blog_post: Mapped[BlogPost] = relationship(back_populates="media")
    name: Mapped[str]
    locations: Mapped[list[str]] = mapped_column(ARRAY(String))
    media_type: Mapped[str]
    position: Mapped[int | None]
    created_timestamp: Mapped[DateTimeIndexed]
    # locations_to_list() removed — .locations is already list[str]
```

#### 2. `app/services/media/media_handler.py`

Four functions change return types. No logic changes — the only edit is how the result is assembled and returned.

**`save_image`** — change the early-return single-path branches to return `[path]`, and the multi-path branch to return a list instead of a joined string:

```python
def save_image(name: str, image_file: MediaFileProtocol) -> list[str]:
    """Save an image, and its webp version."""
    og_image_path = BLOG_UPLOAD_FOLDER / _fix_name_suffix(name)

    if og_image_path.suffix.casefold() in {".gif", ".svg", ".webp"}:
        og_image_path.write_bytes(image_file.read())
        return [get_path_str_from_static(og_image_path)]

    try:
        pil_save(
            pic=image_file,
            filepath=og_image_path,
            max_width=1200,
            max_height=1200,
            quality=90,
        )
    except PIL.UnidentifiedImageError:
        og_image_path.write_bytes(image_file.read())
        images: Iterable[Path] = (og_image_path,)
    else:
        webp_image_path = convert_image(og_image_path)
        if compare_image_sizes(og_image_path, webp_image_path):
            webp_image_path.unlink()
        images = (path for path in (webp_image_path, og_image_path) if path.exists())
    return [get_path_str_from_static(image) for image in images]
```

**`save_video`** — wrap the return value in a list:

```python
def save_video(name: str, video: MediaFileProtocol) -> list[str]:
    """Save a video."""
    video_path = BLOG_UPLOAD_FOLDER / name
    video_path.write_bytes(video.read())
    return [get_path_str_from_static(video_path)]
```

**`save_media`** — update return type annotation and docstring (drop the "comma-separated" sentence):

```python
def save_media(media: UploadFile, name: str) -> tuple[list[str], str]:
    """Save a media file.

    Returns
    -------
        A tuple of the list of path strings and the media type.

        Images save a webp version as well as the original,
        if the webp version is smaller.

    """
    media_type = get_media_type_from_file(media)
    if media_type == MediaType.IMAGE:
        return save_image(name, media.file), media_type
    if media_type == MediaType.VIDEO:
        return save_video(name, media.file), media_type
    msg = f"Unknown media type {media_type}"
    raise ValueError(msg)
```

**`upload_blog_media`** — update return type annotation and docstring:

```python
def upload_blog_media(media: UploadFile, name: str) -> tuple[list[str], str]:
    """Upload a blog media file.

    Returns
    -------
        A tuple of the list of path strings and the media type.

    See `save_media` for more details.

    """
    name = secure_filename(f"{name}.{get_suffix(media)}")
    return save_media(media, name)
```

#### 3. `app/services/blog/blog_handler.py`

**`_save_bp_media`** — update return type annotation only (the call to `upload_blog_media` already returns the right shape after step 2):

```python
def _save_bp_media(
    name: str, blog_post_slug: str, media: UploadFile
) -> tuple[list[str], str]:
    file_name = f"{blog_utils.get_slug(name)}--{blog_post_slug}"
    return media_handler.upload_blog_media(
        media=media,
        name=file_name,
    )
```

**`save_media_for_blog_post`** — rename the local variable from `locations_str` to `locations` and update the `commit_media_to_db` call:

```python
async def save_media_for_blog_post(
    db: AsyncSession,
    blog_post: db_models.BlogPost,
    media: UploadFile,
    name: str,
) -> db_models.BlogPost:
    """Save media for a blog post."""
    locations, media_type = _save_bp_media(
        name=name, blog_post_slug=blog_post.slug, media=media
    )
    return await commit_media_to_db(
        db=db,
        blog_post=blog_post,
        name=name,
        locations=locations,
        media_type=media_type,
    )
```

**`commit_media_to_db`** — rename the parameter from `locations_str: str` to `locations: list[str]` and update the model constructor. Also remove the `# noqa: PLR0913` comment if the argument count drops below 6 — but it still has 6 params (db, blog_post, name, locations, media_type, position), so the noqa stays.

```python
async def commit_media_to_db(  # noqa: PLR0913 (too-many-arguments)
    db: AsyncSession,
    *,
    blog_post: db_models.BlogPost,
    name: str,
    locations: list[str],
    media_type: str,
    position: int | None = None,
) -> db_models.BlogPost:
    """Commit a blog post media to the database."""
    bp_media_object = db_models.BlogPostMedia(
        blog_post_id=blog_post.id,
        name=name,
        locations=locations,
        media_type=media_type,
        created_timestamp=datetime.now(UTC),
        position=position,
    )
    db.add(bp_media_object)
    await db.commit()
    await db.refresh(blog_post)
    return blog_post
```

**`delete_media_from_blog_post`** — replace `media.locations_to_list()` with `media.locations` (already a `list[str]`):

```python
media_locations = media.locations
for location in media_locations:
    media_handler.del_media_from_path_str(location)
```

#### 4. `app/web/html/templates/blog/partials/list_post_media.html`

Replace line 60:

```jinja
{# Before: #}
{% set locations = media_item.locations_to_list() %}

{# After: #}
{% set locations = media_item.locations %}
```

All subsequent uses of `locations` in the template (indexing with `[0]`, `[-1]`, `[:-1]`, iteration) continue to work identically because `media_item.locations` is now a `list[str]`.

#### 5. `tests/model_fixtures.py`

Update the three `commit_media_to_db` calls in `add_blog_post_with_media` to use `locations` (keyword, list of strings) instead of `locations_str`:

```python
await blog_handler.commit_media_to_db(
    db=db_session,
    blog_post=bp,
    name="Some media 1",
    locations=["some_location1.png"],
    media_type="image/png",
)
await blog_handler.commit_media_to_db(
    db=db_session,
    blog_post=bp,
    name="Some media 2",
    locations=["some_location2.png"],
    media_type="image/png",
)
await blog_handler.commit_media_to_db(
    db=db_session,
    blog_post=bp,
    name="Some media 3",
    locations=["some_location3.png"],
    media_type="image/png",
    position=2,
)
```

#### 6. Alembic migration

Generate a skeleton with:

```shell
python -m scripts.alembic migrate -m "locations_string_to_array"
```

Then hand-edit the generated file to perform the data migration. The upgrade converts the existing `VARCHAR` column to `ARRAY(String)` using PostgreSQL's `string_to_array` function. The downgrade reverses it with `array_to_string`.

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # Add the new array column alongside the old string column
    op.add_column(
        "blog_post_media",
        sa.Column("locations_array", postgresql.ARRAY(sa.String()), nullable=True),
    )
    # Populate it from the existing comma-separated string column
    op.execute(
        "UPDATE blog_post_media SET locations_array = string_to_array(locations, ',')"
    )
    # Drop the old column and rename the new one
    op.drop_column("blog_post_media", "locations")
    op.alter_column(
        "blog_post_media",
        "locations_array",
        new_column_name="locations",
        nullable=False,
    )


def downgrade() -> None:
    # Add a temporary text column
    op.add_column(
        "blog_post_media",
        sa.Column("locations_str", sa.String(), nullable=True),
    )
    # Convert the array back to a comma-separated string
    op.execute(
        "UPDATE blog_post_media SET locations_str = array_to_string(locations, ',')"
    )
    # Drop the array column and rename the text column back
    op.drop_column("blog_post_media", "locations")
    op.alter_column(
        "blog_post_media", "locations_str", new_column_name="locations", nullable=False
    )
```

### Testing Approach

No new test files are needed. The existing test suite already provides comprehensive coverage of the affected code paths:

- **`tests/functional_tests/html_tests/blog/test_blog_media.py`** — upload, reorder, and delete tests exercise the entire stack (handler → DB → template render). These will confirm that media created via the array column renders correctly in the template.
- **`tests/model_fixtures.py`** — once updated to pass `locations=["some_location_N.png"]`, the `blog_post_with_media` fixture continues to seed data that the reorder/delete tests consume.

After implementation, run `pytest` (unit + functional only, the default) to confirm all tests pass. The migration itself can be verified manually by running `python -m scripts.alembic migrate -m "..."` against the local Postgres instance before running the test suite.

### Trade-offs and Considerations

**PostgreSQL-only**: `ARRAY(String)` is a PostgreSQL dialect type. The project already targets PostgreSQL exclusively (the `TSVector` column and `gin` indexes prove this), so there is no portability regression.

**Migration column-swap approach**: The upgrade adds a new nullable column, populates it, drops the old column, then renames. This is safe for a development/single-node deployment but on a live production table it would cause a brief `ACCESS EXCLUSIVE` lock per `ALTER TABLE`. For the scale of this project that is acceptable. An alternative zero-downtime approach (add column, backfill in batches, deploy new code, drop old column) is overkill here.

**Downgrade behaviour with multi-path rows**: On downgrade, `array_to_string(locations, ',')` faithfully reconstructs the original comma-separated string for rows that have multiple paths. The old `locations_to_list()` split on `,` with no trimming, so roundtrip fidelity is exact as long as no path ever contained a comma — which is structurally impossible given that paths come from `secure_filename` + filesystem paths.

**`locations_to_list()` in templates**: Jinja2 templates are not type-checked. The change from `media_item.locations_to_list()` to `media_item.locations` is a one-line edit; a runtime error during a test render would surface any missed call site immediately.

---

## Tasks

### Phase 1: ORM Model

- [x] In `app/datastore/db_models.py`, add `ARRAY` to the `from sqlalchemy.dialects.postgresql import ...` line.
- [x] Change `locations: Mapped[str]` to `locations: Mapped[list[str]] = mapped_column(ARRAY(String))`.
- [x] Update the `BlogPostMedia` class docstring to remove the "comma-separated" language.
- [x] Remove the `locations_to_list()` method entirely.

### Phase 2: Media Handler

- [x] In `app/services/media/media_handler.py`, change `save_image()` return type from `str` to `list[str]` and update its return statements to return a list.
- [x] Change `save_video()` return type from `str` to `list[str]` and wrap the return value in a list.
- [x] Change `save_media()` return type from `tuple[str, str]` to `tuple[list[str], str]` and update the docstring.
- [x] Change `upload_blog_media()` return type from `tuple[str, str]` to `tuple[list[str], str]` and update the docstring.

### Phase 3: Blog Handler

- [x] In `app/services/blog/blog_handler.py`, update `_save_bp_media()` return type annotation to `tuple[list[str], str]`.
- [x] In `save_media_for_blog_post()`, rename the local variable `locations_str` to `locations` and update the `commit_media_to_db` keyword argument accordingly.
- [x] In `commit_media_to_db()`, rename the parameter `locations_str: str` to `locations: list[str]`.
- [x] In `delete_media_from_blog_post()`, replace `media.locations_to_list()` with `media.locations`.

### Phase 4: Template

- [x] In `app/web/html/templates/blog/partials/list_post_media.html`, replace `media_item.locations_to_list()` with `media_item.locations`.

### Phase 5: Test Fixtures

- [x] In `tests/model_fixtures.py`, update all three `commit_media_to_db` calls in `add_blog_post_with_media` to use `locations=["some_location_N.png"]` instead of `locations_str="some_location_N.png"`.

### Phase 6: Alembic Migration

- [x] Generate a migration skeleton: `python -m scripts.alembic migrate -m "locations_string_to_array"`.
- [x] Hand-edit the generated migration file to implement the `upgrade()` (add nullable array column, `UPDATE … SET locations_array = string_to_array(locations, ',')`, drop old column, rename) and `downgrade()` (add nullable text column, `UPDATE … SET locations_str = array_to_string(locations, ',')`, drop array column, rename) steps.

### Phase 7: Lint & Verify

- [x] Run `pre-commit run --all-files` and fix any issues.
- [x] Run `pytest` and confirm all tests pass.

---

## Implementation

> **AI instructions:** Implement all tasks from the checklist above. Follow these rules throughout:
>
> - Implement everything — do not cherry-pick tasks.
> - Mark each task `[x]` in the Tasks section immediately after completing it.
> - Do not stop until all tasks are marked complete.
> - After each logical change, run `pre-commit run --all-files` to catch lint and formatting issues before continuing.
> - Do not add unnecessary comments, docstrings, or type annotations to code you did not change.
> - Do not use `print` statements; use the `logging` module instead.
> - Do not change function signatures unless the plan explicitly requires it.
> - If a task surfaces a problem not covered by the plan, stop and note it here rather than making unplanned changes.

### Implementation Log

[AI: note any significant decisions, surprises, or deviations from the plan encountered during implementation.]
