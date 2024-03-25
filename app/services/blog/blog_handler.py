"""blog_handler: service for manipulating blog posts."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from http import HTTPStatus
from logging import getLogger
from typing import Self

import sqlalchemy
from fastapi import UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.datastore import db_models
from app.services.blog import blog_utils, markdown_parser
from app.services.general import transforms
from app.services.media import media_handler
from app.web import errors, web_models
from app.web.web_models import UnauthenticatedUser

logger = getLogger(__name__)
ERROR_SAVING_BP = "Error saving blog post"


class SaveBlogInput(BaseModel, arbitrary_types_allowed=True):
    """Input data model for saving a blog post."""

    existing_bp: db_models.BlogPost | None = None
    title: str
    tags: transforms.CoercedList = []
    can_comment: transforms.CoercedBool = True
    is_published: transforms.CoercedBool = False
    description: str
    content: str
    thumbnail_url: str | None = None

    # These 2 only work for creating new blog posts
    # and are only here for testing purposes
    likes: int = 0
    views: int = 0


class SaveBlogResponse(BaseModel, arbitrary_types_allowed=True):
    """Response for saving a blog post."""

    success: bool = True
    blog_post: db_models.BlogPost | None = None
    err_msg: str = ERROR_SAVING_BP
    status_code: HTTPStatus = HTTPStatus.OK
    field_errors: defaultdict[str, list[str]] = defaultdict(list)


class CommentInputPreview(BaseModel, arbitrary_types_allowed=True):
    """Input for comment preview."""

    bp_id: int
    guest_id: str | None = None
    user_id: int | None = None
    name: str | None = None
    email: str | None = None
    content: str


class SaveCommentInput(CommentInputPreview):
    """Input data model for saving a blog post comment."""

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
    status_code: HTTPStatus = HTTPStatus.OK
    field_errors: defaultdict[str, list[str]] = defaultdict(list)


def _get_bp_statement() -> Select:
    return select(db_models.BlogPost).options(
        selectinload(db_models.BlogPost.tags),
        selectinload(db_models.BlogPost.media),
        selectinload(db_models.BlogPost.comments).selectinload(db_models.BlogPostComment.user),
        selectinload(db_models.BlogPost.old_slugs),
    )


class Paginator(BaseModel, arbitrary_types_allowed=True):
    """Response for getting blog posts."""

    blog_posts: list[db_models.BlogPost] = Field(repr=False)
    min_result: int
    max_result: int
    total_results: int
    total_pages: int
    current_page: int
    is_first_page: bool = False
    is_last_page: bool = False
    is_only_page: bool = False


async def get_blog_posts(  # noqa: PLR0913 (too-many-arguments)
    *,
    db: AsyncSession,
    can_see_unpublished: bool,
    search: str | None = None,
    tags: str | None = None,
    order_by_field: str = "created_timestamp",
    asc: bool = False,
    results_per_page: int = 20,
    page: int = 1,
) -> Paginator:
    """Get blog posts."""
    stmt = _get_bp_statement()
    count_stmt = select(sqlalchemy.func.count()).select_from(db_models.BlogPost)
    if not can_see_unpublished:
        stmt = stmt.filter(db_models.BlogPost.is_published.is_(True))
        count_stmt = count_stmt.where(db_models.BlogPost.is_published.is_(True))
    if tags:
        tags_list = transforms.to_list(tags, lowercase=True)
        stmt = stmt.filter(db_models.BlogPost.tags.any(db_models.BlogPostTag.tag.in_(tags_list)))
        count_stmt = count_stmt.where(
            db_models.BlogPost.tags.any(db_models.BlogPostTag.tag.in_(tags_list))
        )
    if search:
        stmt = stmt.filter(db_models.BlogPost.ts_vector.match(search))
        count_stmt = count_stmt.where(db_models.BlogPost.ts_vector.match(search))

    # Get total blog posts matching results here
    count_result = await db.execute(count_stmt)
    total_results = count_result.scalar() or 0
    total_pages = _calculate_total_pages(
        total_results=total_results, results_per_page=results_per_page
    )
    actual_page = min(page, total_pages)
    actual_page = max(actual_page, 1)

    order_by = getattr(db_models.BlogPost, order_by_field)
    if not asc:
        order_by = order_by.desc()
    limit, offset = _calculate_limit_offset(results_per_page=results_per_page, page=actual_page)
    stmt = stmt.order_by(order_by).limit(limit).offset(offset)
    result = await db.execute(stmt)
    blog_posts = list(result.scalars().all())
    return Paginator(
        blog_posts=blog_posts,
        min_result=offset + 1,
        max_result=offset + len(blog_posts),
        total_results=total_results,
        total_pages=total_pages,
        current_page=actual_page,
        is_first_page=actual_page == 1,
        is_last_page=actual_page == total_pages,
        is_only_page=total_pages == 1,
    )


def _calculate_total_pages(*, total_results: int, results_per_page: int) -> int:
    """Calculate the total number of pages."""
    return (total_results + results_per_page - 1) // results_per_page


def _calculate_limit_offset(*, results_per_page: int, page: int) -> tuple[int, int]:
    """Calculate the limit and offset for a query."""
    limit = results_per_page
    return limit, (page - 1) * limit


async def get_bp_from_id(
    *, db: AsyncSession, bp_id: int, for_update: bool = False
) -> db_models.BlogPost:
    """Get a blog post from its ID."""
    try:
        stmt = _get_bp_statement().filter(db_models.BlogPost.id == bp_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        return result.scalars().one()
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostNotFoundError from e


async def get_bp_from_slug(db: AsyncSession, slug: str) -> db_models.BlogPost:
    """Get a blog post from its slug."""
    try:
        stmt = _get_bp_statement().filter(db_models.BlogPost.slug == slug)
        result = await db.execute(stmt)
        return result.scalars().one()
    except sqlalchemy.exc.NoResultFound:
        # FIXME: This maybe should raise an error that redirects to the new slug
        return await _get_bp_from_slug_history(db=db, slug=slug)


async def _get_bp_from_slug_history(db: AsyncSession, slug: str) -> db_models.BlogPost:
    """Get a blog post from its slug history."""
    try:
        stmt = (
            select(db_models.OldBlogPostSlug)
            .options(
                selectinload(db_models.OldBlogPostSlug.blog_post)
                .selectinload(db_models.BlogPost.comments)
                .selectinload(db_models.BlogPostComment.user),
                selectinload(db_models.OldBlogPostSlug.blog_post).selectinload(
                    db_models.BlogPost.tags
                ),
            )
            .filter(db_models.OldBlogPostSlug.slug == slug)
        )
        result = await db.execute(stmt)
        slug_object = result.scalars().one()
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostNotFoundError from e
    else:
        return slug_object.blog_post


async def save_blog_post(db: AsyncSession, data: SaveBlogInput) -> SaveBlogResponse:
    """Save a blog post."""
    SaveBlogResponse.model_rebuild()

    field_errors: defaultdict[str, list[str]] = defaultdict(list)
    try:
        blog_post = await _save_bp_to_db(data=data, db=db)
    except sqlalchemy.exc.IntegrityError as e:
        return await _create_bp_save_sqlalchemy_error_response(
            db=db,
            e=e,
            field_errors=field_errors,
        )
    await db.refresh(blog_post)
    return SaveBlogResponse(
        success=True,
        blog_post=blog_post,
        message="Blog post saved successfully",
        field_errors=field_errors,
    )


async def _save_bp_to_db(
    *,
    data: SaveBlogInput,
    db: AsyncSession,
) -> db_models.BlogPost:
    """Create or update a blog post and save it to the database."""
    if data.existing_bp:
        blog_post = await update_existing_bp_fields(
            db=db,
            data=data,
        )
    else:
        blog_post = await create_new_bp(db=db, data=data)

    await db.commit()
    return blog_post


async def update_existing_bp_fields(
    *,
    db: AsyncSession,
    data: SaveBlogInput,
) -> db_models.BlogPost:
    """Update an existing blog post's fields."""
    blog_post = data.existing_bp
    # For mypy, can't actually be None at this point
    assert blog_post is not None  # noqa: S101 (assert)

    if blog_post.title != data.title:
        stmt = select(db_models.OldBlogPostSlug).filter(
            db_models.OldBlogPostSlug.slug == blog_post.slug
        )
        result = await db.execute(stmt)
        old_slug = result.scalars().first() or db_models.OldBlogPostSlug(
            slug=blog_post.slug, blog_post=blog_post
        )
        blog_post.old_slugs.append(old_slug)
        blog_post.title = data.title
        blog_post.slug = blog_utils.get_slug(data.title)
    current_tags = {tag.tag for tag in blog_post.tags}
    if current_tags != set(data.tags):
        blog_post.tags = await _get_bp_tags(db=db, tags=data.tags)
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
    if blog_post.thumbnail_location != data.thumbnail_url:
        blog_post.thumbnail_location = data.thumbnail_url
    blog_post.updated_timestamp = datetime.now().astimezone(timezone.utc)
    return blog_post


async def create_new_bp(
    *,
    db: AsyncSession,
    data: SaveBlogInput,
) -> db_models.BlogPost:
    """Create a new blog post and add it to the database transaction."""
    blog_post = await set_new_bp_fields(data=data, db=db)
    db.add(blog_post)
    return blog_post


async def set_new_bp_fields(
    data: SaveBlogInput, db: AsyncSession | None = None
) -> db_models.BlogPost:
    """Set fields for a new blog post.

    Can ignore db session if not expecting to add the blog post to the database.
    """
    html_description = markdown_parser.markdown_to_html(data.description)
    html_content = markdown_parser.markdown_to_html(data.content)
    tags = await _get_bp_tags(db=db, tags=data.tags)
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
        likes=data.likes,
        views=data.views,
        thumbnail_location=data.thumbnail_url,
    )


async def _get_bp_tags(
    tags: Iterable[str], db: AsyncSession | None = None
) -> list[db_models.BlogPostTag]:
    """Get blog post tags from the database or create new ones."""
    tags = list(set(tags))
    existing_tags = await _get_existing_bp_tags_from_list(tags=tags, db=db)
    return [
        existing_tags[tag] if tag in existing_tags else db_models.BlogPostTag(tag=tag)
        for tag in tags
    ]


async def _get_existing_bp_tags_from_list(
    tags: Iterable[str], db: AsyncSession | None = None
) -> dict[str, db_models.BlogPostTag]:
    """Get blog post tags from the database or create new ones."""
    if not db:
        return {}
    tags = list(set(tags))
    stmt = select(db_models.BlogPostTag).filter(db_models.BlogPostTag.tag.in_(tags))
    result = await db.execute(stmt)
    return {tag.tag: tag for tag in result.scalars().all()}


async def _create_bp_save_sqlalchemy_error_response(
    db: AsyncSession,
    e: sqlalchemy.exc.IntegrityError,
    field_errors: defaultdict[str, list[str]],
) -> SaveBlogResponse:
    """Create a response for a SQLAlchemy IntegrityError.

    Side effects:
    - Rollback the database session
    - Update the field_errors dict
    """
    logger.exception(ERROR_SAVING_BP)
    await db.rollback()
    err = str(e)
    msg = ERROR_SAVING_BP

    if ("duplicate key value violates unique constraint" in err) and (
        "ix_blog_posts_slug" in err or "ix_blog_posts_title" in err
    ):
        field_errors["title"].append("Title already exists")
    else:  # pragma: no cover (don't know what other errors could happen)
        msg = err
    return SaveBlogResponse(
        success=False,
        message=msg,
        field_errors=field_errors,
    )


async def save_media_for_blog_post(
    db: AsyncSession,
    blog_post: db_models.BlogPost,
    media: UploadFile,
    name: str,
) -> db_models.BlogPost:
    """Save media for a blog post."""
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


async def reorder_media_for_blog_post(
    db: AsyncSession,
    media_id: int,
    bp_id: int,
    position: int | None,
) -> db_models.BlogPost:
    """Reorder media for a blog post."""
    stmt = select(db_models.BlogPostMedia).filter(db_models.BlogPostMedia.id == media_id)
    result = await db.execute(stmt)
    try:
        media = result.scalars().one()
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostMediaNotFoundError from e
    media.position = position
    await db.commit()
    return await get_bp_from_id(db=db, bp_id=bp_id)


async def delete_media_from_blog_post(
    db: AsyncSession,
    media_id: int,
    bp_id: int,
) -> db_models.BlogPost:
    """Delete media from a blog post."""
    blog_post = await get_bp_from_id(db=db, bp_id=bp_id)
    stmt = select(db_models.BlogPostMedia).filter(db_models.BlogPostMedia.id == media_id)
    result = await db.execute(stmt)
    try:
        media = result.scalars().one()
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostMediaNotFoundError from e
    media_locations = media.locations_to_list()
    for location in media_locations:
        media_handler.del_media_from_path_str(location)
    await db.delete(media)
    await db.commit()
    await db.refresh(blog_post)
    return blog_post


def _save_bp_media(name: str, blog_post_slug: str, media: UploadFile) -> tuple[str, str]:
    file_name = f"{blog_utils.get_slug(name)}--{blog_post_slug}"
    return media_handler.upload_blog_media(
        media=media,
        name=file_name,
    )


async def commit_media_to_db(  # noqa: PLR0913 (too-many-arguments)
    db: AsyncSession,
    *,
    blog_post: db_models.BlogPost,
    name: str,
    locations_str: str,
    media_type: str,
    position: int | None = None,
) -> db_models.BlogPost:
    """Commit a blog post media to the database."""
    bp_media_object = db_models.BlogPostMedia(
        blog_post_id=blog_post.id,
        name=name,
        locations=locations_str,
        media_type=media_type,
        created_timestamp=datetime.now().astimezone(timezone.utc),
        position=position,
    )
    db.add(bp_media_object)
    await db.commit()
    await db.refresh(blog_post)
    return blog_post


async def toggle_blog_post_like(
    *, db: AsyncSession, bp: db_models.BlogPost, like: bool
) -> db_models.BlogPost:
    """Toggle a blog post like."""
    if like:
        bp.likes = db_models.BlogPost.likes + 1
    else:
        bp.likes = db_models.BlogPost.likes - 1
    await db.commit()
    return bp


async def save_new_comment(db: AsyncSession, data: SaveCommentInput) -> SaveCommentResponse:
    """Save a blog post comment."""
    comment = generate_comment(data=data)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return SaveCommentResponse(success=True, comment=comment)


async def update_existing_comment(
    db: AsyncSession,
    current_user: db_models.User | web_models.UnauthenticatedUser,
    comment: db_models.BlogPostComment,
    md_content: str,
) -> db_models.BlogPostComment:
    """Update an existing blog post comment."""
    html_content = generate_comment_html(md_content)
    comment.md_content = md_content
    comment.html_content = html_content
    comment.updated_timestamp = datetime.now().astimezone(timezone.utc)
    if current_user.is_authenticated:
        comment.user_id = current_user.id
    await db.commit()
    await db.refresh(comment)
    return comment


def generate_comment(data: CommentInputPreview) -> db_models.BlogPostComment:
    """Generate a blog post comment."""
    html_content = generate_comment_html(data.content)
    now = datetime.now().astimezone(timezone.utc)
    return db_models.BlogPostComment(
        blog_post_id=data.bp_id,
        name=data.name,
        email=data.email,
        user_id=data.user_id,
        guest_id=data.guest_id,
        md_content=data.content,
        html_content=html_content,
        created_timestamp=now,
        updated_timestamp=now,
        likes=0,
    )


def generate_comment_html(content: str) -> str:
    """Generate HTML for a comment, with proper sanitization."""
    sanitized_before = markdown_parser.clean_with_exceptions(content)
    html = markdown_parser.markdown_to_html(sanitized_before, update_headers=False).content
    html = markdown_parser.convert_h_tags(html)
    return markdown_parser.bleach_comment_html(html)


async def delete_comment(
    db: AsyncSession,
    comment_id: int,
    current_user: db_models.User | UnauthenticatedUser,
) -> SaveCommentResponse:
    """Delete a blog post comment."""
    comment = await get_comment_from_id(db=db, comment_id=comment_id)
    if not can_delete_comment(comment=comment, current_user=current_user):
        return SaveCommentResponse(
            success=False,
            err_msg="You do not have permission to delete this comment.",
            status_code=HTTPStatus.FORBIDDEN,
            comment=comment,
        )
    await db.delete(comment)
    await db.commit()
    return SaveCommentResponse(success=True)


def can_edit_comment(
    comment: db_models.BlogPostComment, current_user: db_models.User | UnauthenticatedUser
) -> bool:
    """Check if a user can edit this comment."""
    return comment.user_id == current_user.id or comment.guest_id == current_user.guest_id


def can_delete_comment(
    comment: db_models.BlogPostComment, current_user: db_models.User | UnauthenticatedUser
) -> bool:
    """Check if a user can delete this comment. Allows admin to delete any comment."""
    return (
        comment.user_id == current_user.id
        or comment.guest_id == current_user.guest_id
        or current_user.is_admin
    )


async def get_comment_from_id(db: AsyncSession, comment_id: int) -> db_models.BlogPostComment:
    """Get a comment from its ID."""
    try:
        stmt = (
            select(db_models.BlogPostComment)
            .options(
                selectinload(db_models.BlogPostComment.blog_post),
                selectinload(db_models.BlogPostComment.user),
            )
            .filter(db_models.BlogPostComment.id == comment_id)
        )
        result = await db.execute(stmt)
        return result.scalars().one()
    except sqlalchemy.exc.NoResultFound as e:
        raise errors.BlogPostCommentNotFoundError from e
