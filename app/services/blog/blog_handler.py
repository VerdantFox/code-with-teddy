"""blog_handler: service for manipulating blog posts."""
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from logging import getLogger
from typing import Self

import sqlalchemy
from fastapi import UploadFile
from pydantic import BaseModel, model_validator

from app.datastore import db_models
from app.datastore.database import Session
from app.services.blog import blog_utils, markdown_parser
from app.services.general import transforms
from app.services.media import media_handler
from app.web import errors

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


class SaveCommentInput(BaseModel, arbitrary_types_allowed=True):
    """Input data model for saving a blog post comment."""

    bp_id: int
    guest_id: str | None = None
    user_id: int | None = None
    name: str | None = None
    email: str | None = None
    content: str
    parent_id: int | None = None

    @model_validator(mode="after")
    def check_user_id_or_name(self) -> Self:
        """Check that either user_id or name are provided."""
        if not self.user_id and not self.name:
            msg = "Must provide either user_id or name"
            raise ValueError(msg)
        return self


class SaveCommentResponse(BaseModel, arbitrary_types_allowed=True):
    """Response for saving a blog post comment."""

    success: bool = True
    comment: db_models.BlogPostComment | None = None
    err_msg: str = "Error saving comment"
    field_errors: defaultdict[str, list[str]] = defaultdict(list)


def get_bp_from_id(*, db: Session, bp_id: int, for_update: bool = False) -> db_models.BlogPost:
    """Get a blog post from its ID."""
    try:
        query = db.query(db_models.BlogPost).filter(db_models.BlogPost.id == bp_id)
        if for_update:
            query = query.with_for_update()
        return query.one()
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostNotFoundError from e


def get_bp_from_slug(db: Session, slug: str) -> db_models.BlogPost:
    """Get a blog post from its slug."""
    try:
        return db.query(db_models.BlogPost).filter(db_models.BlogPost.slug == slug).one()
    except sqlalchemy.exc.NoResultFound:
        # FIXME: This maybe should raise an error that redirects to the new slug
        return _get_bp_from_slug_history(db=db, slug=slug)


def _get_bp_from_slug_history(db: Session, slug: str) -> db_models.BlogPost:
    """Get a blog post from its slug history."""
    try:
        return (
            db.query(db_models.OldBlogPostSlug)
            .filter(db_models.OldBlogPostSlug.slug == slug)
            .one()
            .blog_post
        )
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostNotFoundError from e


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


def save_media_for_blog_post(
    db: Session,
    blog_post: db_models.BlogPost,
    media: UploadFile,
    name: str,
) -> db_models.BlogPost:
    """Save media for a blog post."""
    locations_str, media_type = _save_bp_media(
        name=name, blog_post_slug=blog_post.slug, media=media
    )
    return _commit_bp_to_db(
        db=db,
        blog_post=blog_post,
        name=name,
        locations_str=locations_str,
        media_type=media_type,
    )


def delete_media_from_blog_post(
    db: Session,
    media_id: int,
    bp_id: int,
) -> db_models.BlogPost:
    """Delete media from a blog post."""
    blog_post = get_bp_from_id(db=db, bp_id=bp_id)
    media = db.query(db_models.BlogPostMedia).filter(db_models.BlogPostMedia.id == media_id).one()
    media_locations = media.locations_to_list()
    for location in media_locations:
        media_handler.del_media_from_path_str(location)
    db.delete(media)
    db.commit()
    db.refresh(blog_post)
    return blog_post


def _save_bp_media(name: str, blog_post_slug: str, media: UploadFile) -> tuple[str, str]:
    file_name = f"{blog_utils.get_slug(name)}--{blog_post_slug}"
    return media_handler.upload_blog_media(
        media=media,
        name=file_name,
    )


def _commit_bp_to_db(
    db: Session, blog_post: db_models.BlogPost, name: str, locations_str: str, media_type: str
) -> db_models.BlogPost:
    """Commit a blog post to the database."""
    bp_media_object = db_models.BlogPostMedia(
        blog_post_id=blog_post.id,
        name=name,
        locations=locations_str,
        media_type=media_type,
    )
    db.add(bp_media_object)
    db.commit()
    db.refresh(blog_post)
    return blog_post


def toggle_blog_post_like(*, db: Session, bp: db_models.BlogPost, like: bool) -> db_models.BlogPost:
    """Toggle a blog post like."""
    if like:
        bp.likes += 1
    else:
        bp.likes -= 1
    db.commit()
    return bp


def save_new_comment(db: Session, data: SaveCommentInput) -> SaveCommentResponse:
    """Save a blog post comment."""
    comment = generate_comment(data=data)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return SaveCommentResponse(success=True, comment=comment)


def generate_comment(data: SaveCommentInput) -> db_models.BlogPostComment:
    """Generate a blog post comment."""
    html_content = generate_comment_html(data.content)
    return db_models.BlogPostComment(
        blog_post_id=data.bp_id,
        name=data.name,
        email=data.email,
        user_id=data.user_id,
        guest_id=data.guest_id,
        md_content=data.content,
        html_content=html_content,
        created_timestamp=datetime.now().astimezone(timezone.utc),
        updated_timestamp=datetime.now().astimezone(timezone.utc),
        likes=0,
        parent_id=data.parent_id,
    )


def generate_comment_html(content: str) -> str:
    """Generate HTML for a comment, with proper sanitization."""
    sanitized_before = markdown_parser.clean_except_code_blocks(content)
    html = markdown_parser.markdown_to_html(sanitized_before, update_headers=False).content
    html = markdown_parser.convert_h_tags(html)
    return markdown_parser.bleach_comment_html(html)
