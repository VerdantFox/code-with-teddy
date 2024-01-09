"""blog_handler: service for manipulating blog posts."""
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from logging import getLogger

import sqlalchemy
from pydantic import BaseModel

from app.datastore import db_models
from app.datastore.database import Session
from app.services.blog import blog_utils, markdown_parser
from app.services.general import transforms

logger = getLogger(__name__)
ERROR_SAVING_BP = "Error saving blog post"


class SaveBlogInput(BaseModel, arbitrary_types_allowed=True):
    """Input data model for saving a blog post."""

    existing_bp: db_models.BlogPost | None = None
    title: str
    tags: transforms.CoercedList
    can_comment: transforms.CoercedBool
    is_published: transforms.CoercedBool
    description: str
    content: str


class SaveBlogResponse(BaseModel, arbitrary_types_allowed=True):
    """Response for saving a blog post."""

    success: bool = True
    blog_post: db_models.BlogPost | None = None
    err_msg: str = ERROR_SAVING_BP
    field_errors: defaultdict[str, list[str]] = defaultdict(list)


def save_blog_post(db: Session, data: SaveBlogInput) -> SaveBlogResponse:
    """Save a blog post."""
    SaveBlogResponse.model_rebuild()

    field_errors: defaultdict[str, list[str]] = defaultdict(list)
    try:
        blog_post = _save_bp_to_db(data=data, db=db)
    except sqlalchemy.exc.IntegrityError as e:
        return _create_bp_save_sqlalchemy_error_response(
            db=db,
            e=e,
            field_errors=field_errors,
        )
    db.refresh(blog_post)
    return SaveBlogResponse(
        success=True,
        blog_post=blog_post,
        message="Blog post saved successfully",
        field_errors=field_errors,
    )


def _save_bp_to_db(
    *,
    data: SaveBlogInput,
    db: Session,
) -> db_models.BlogPost:
    """Create or update a blog post and save it to the database."""
    if data.existing_bp:
        blog_post = update_existing_bp_fields(
            db=db,
            data=data,
        )
    else:
        blog_post = create_new_bp(db=db, data=data)

    db.commit()
    return blog_post


def update_existing_bp_fields(
    *,
    db: Session,
    data: SaveBlogInput,
) -> db_models.BlogPost:
    """Update an existing blog post's fields."""
    blog_post = data.existing_bp
    # For mypy, can't actually be None at this point
    assert blog_post is not None  # noqa: S101 (assert)

    if blog_post.title != data.title:
        old_slug = db.query(db_models.OldBlogPostSlug).filter(
            db_models.OldBlogPostSlug.slug == blog_post.slug
        ).first() or db_models.OldBlogPostSlug(slug=blog_post.slug, blog_post=blog_post)
        blog_post.old_slugs.append(old_slug)
        blog_post.title = data.title
        blog_post.slug = blog_utils.get_slug(data.title)
    current_tags = {tag.tag for tag in blog_post.tags}
    if current_tags != set(data.tags):
        blog_post.tags = _get_bp_tags(db=db, tags=data.tags)
    if blog_post.is_published != data.is_published:
        blog_post.is_published = data.is_published
    if blog_post.can_comment != data.can_comment:
        blog_post.can_comment = data.can_comment
    if blog_post.markdown_description != data.description:
        blog_post.markdown_description = data.description
        html_description = markdown_parser.markdown_to_html(data.description)
        blog_post.html_description = html_description.content
    if blog_post.markdown_content != data.content:
        blog_post.markdown_content = data.content
        html_content = markdown_parser.markdown_to_html(data.content)
        blog_post.html_content = html_content.content
        blog_post.html_toc = html_content.toc
        blog_post.read_mins = blog_utils.calc_read_mins(data.content)
    blog_post.updated_timestamp = datetime.now().astimezone(timezone.utc)
    return blog_post


def create_new_bp(
    *,
    db: Session,
    data: SaveBlogInput,
) -> db_models.BlogPost:
    """Create a new blog post and add it to the database transaction."""
    blog_post = set_new_bp_fields(data=data, db=db)
    db.add(blog_post)
    return blog_post


def set_new_bp_fields(data: SaveBlogInput, db: Session | None = None) -> db_models.BlogPost:
    """Set fields for a new blog post.

    Can ignore db session if not expecting to add the blog post to the database.
    """
    html_description = markdown_parser.markdown_to_html(data.description)
    html_content = markdown_parser.markdown_to_html(data.content)
    tags = _get_bp_tags(db=db, tags=data.tags)
    now = datetime.now().astimezone(timezone.utc)
    return db_models.BlogPost(
        title=data.title,
        slug=blog_utils.get_slug(data.title),
        tags=tags,
        read_mins=blog_utils.calc_read_mins(data.content),
        is_published=data.is_published,
        can_comment=data.can_comment,
        markdown_description=data.description,
        markdown_content=data.content,
        html_description=html_description.content,
        html_content=html_content.content,
        html_toc=html_content.toc,
        created_timestamp=now,
        updated_timestamp=now,
        likes=0,
        views=0,
    )


def _get_bp_tags(tags: Iterable[str], db: Session | None = None) -> list[db_models.BlogPostTag]:
    """Get blog post tags from the database or create new ones."""
    return [
        (
            db.query(db_models.BlogPostTag).filter(db_models.BlogPostTag.tag == tag).first()
            if db
            else None
        )
        or db_models.BlogPostTag(tag=tag)
        for tag in set(tags)
    ]


def _create_bp_save_sqlalchemy_error_response(
    db: Session,
    e: sqlalchemy.exc.IntegrityError,
    field_errors: defaultdict[str, list[str]],
) -> SaveBlogResponse:
    """Create a response for a SQLAlchemy IntegrityError.

    Side effects:
    - Rollback the database session
    - Update the field_errors dict
    """
    logger.exception(ERROR_SAVING_BP)
    db.rollback()
    err = str(e)
    msg = ERROR_SAVING_BP
    if 'duplicate key value violates unique constraint "ix_blog_posts_slug"' in err:
        field_errors["title"].append("Title already exists")
    else:
        msg = err
    return SaveBlogResponse(
        success=False,
        message=msg,
        field_errors=field_errors,
    )
