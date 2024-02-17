"""landing: HTML routes for landing."""

from logging import getLogger

from fastapi import APIRouter, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from starlette.templating import _TemplateResponse
from wtforms import (
    EmailField,
    FileField,
    HiddenField,
    StringField,
    TextAreaField,
    validators,
)

from app import constants
from app.datastore.database import DBSession
from app.permissions import Action, requires_permission
from app.services.blog import blog_handler
from app.web.auth import LoggedInUser, LoggedInUserOptional
from app.web.html import web_user_handlers
from app.web.html.const import templates
from app.web.html.flash_messages import (
    DEFAULT_FORM_ERROR_MESSAGE,
    FlashCategory,
    FlashMessage,
    FormErrorMessage,
)
from app.web.html.routes.users import LoginForm
from app.web.html.wtform_utils import Form, custom_validators
from app.web.html.wtform_utils.wtform_fields import BooleanField

# ----------- Routers -----------
router = APIRouter(tags=["blog"])

logger = getLogger(__name__)
BLOG_POST = "blog_post"
BLOG_POSTS = "blog_posts"
LIKED = "liked"
EDIT_BP_TEMPLATE = "blog/edit_post.html"
UPLOAD_MEDIA_TEMPLATE = "blog/partials/edit_post_media_form.html"
LIST_MEDIA_TEMPLATE = "blog/partials/list_post_media.html"
FLASH_ERRORS_TEMPLATE = "shared/partials/flash_error_messages.html"
COMMENTS_TEMPLATE = "blog/partials/comments.html"
COMMENT_TEMPLATE = "blog/partials/comment.html"
COMMENT_FORM_TEMPLATE = "blog/partials/comment_form.html"
MEDIA_FORM = "media_form"
COMMENT_FORM = "comment_form"
LIKED_POSTS_COOKIE = "liked_posts"  # Sets a cookie with a list of liked posts, by id
ERROR_SAVING_COMMENT = "Error saving comment"


@router.get("/blog", response_model=None)
async def list_blog_posts(
    request: Request, current_user: LoggedInUserOptional, db: DBSession
) -> _TemplateResponse:
    """Return the blog list page."""
    blog_posts = blog_handler.get_blog_posts(
        db=db,
        can_see_unpublished=current_user.has_permission(Action.READ_UNPUBLISHED_BP),
        order_by_field="created_timestamp",
        asc=False,
        limit=20,
        offset=0,
    )
    return templates.TemplateResponse(
        "blog/list_posts.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.LOGIN_FORM: LoginForm(redirect_url=str(request.url)),
            BLOG_POSTS: blog_posts,
        },
    )


class BlogPostForm(Form):
    """Form for creating and editing blog posts."""

    is_new = BooleanField("Is new", default=False)
    title = StringField("Title", description="My cool post")
    tags = StringField(
        "Tags", validators=[validators.optional()], description="python, fastapi, web"
    )
    can_comment = BooleanField("Allow Comments", default=True)
    is_published = BooleanField("Publish", default=False)
    description = TextAreaField(
        "Description",
        description="Short markdown description (couple paragraphs)",
        validators=[validators.Length(min=1)],
    )
    content = TextAreaField(
        "Content",
        description="Markdown content (the whole blog post)",
        validators=[validators.Length(min=1)],
    )
    thumbnail_url: StringField = StringField(
        "Thumbnail URL",
        description="https://example.com/thumbnail.png",
        validators=[
            validators.optional(),
            validators.Length(min=1, max=2000),
        ],
    )


@router.get("/blog/create", response_model=None)
@requires_permission(Action.EDIT_BP)
async def create_bp_get(request: Request, current_user: LoggedInUser) -> _TemplateResponse:
    """Return page to create a blog post."""
    return templates.TemplateResponse(
        EDIT_BP_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.FORM: BlogPostForm(is_new=True),
        },
    )


@router.post("/blog/create", response_model=None)
@requires_permission(Action.EDIT_BP)
async def create_bp_post(
    request: Request, current_user: LoggedInUser, db: DBSession
) -> _TemplateResponse | RedirectResponse:
    """Post the blog post create form."""
    form_data = await request.form()
    form = BlogPostForm.load(form_data)
    if not form.validate():
        return templates.TemplateResponse(
            EDIT_BP_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.FORM: form,
                constants.MESSAGE: FormErrorMessage(),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    input_data = blog_handler.SaveBlogInput(**form.data)
    response = blog_handler.save_blog_post(db, input_data)
    if not response.success or not response.blog_post:
        for error_field, error_msg in response.field_errors.items():
            form[error_field].errors.extend(error_msg)
        return templates.TemplateResponse(
            EDIT_BP_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.FORM: form,
                constants.MESSAGE: FormErrorMessage(text=response.err_msg),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    FlashMessage(
        title="Blog Post Saved!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        url=request.url_for("html:edit_bp_get", bp_id=response.blog_post.id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _get_liked_posts_from_cookie(request: Request) -> set[int]:
    """Get the liked posts from the cookie."""
    return {int(id_) for id_ in request.cookies.get(LIKED_POSTS_COOKIE, "").split(",") if id_}


@router.get("/blog/{slug}", response_model=None)
async def read_blog_post(
    request: Request, current_user: LoggedInUserOptional, db: DBSession, slug: str
) -> _TemplateResponse:
    """Return page to read a blog post.

    NOTE: This route needs to be after the create_bp_get route,
    otherwise it will match.
    """
    bp = blog_handler.get_bp_from_slug(db=db, slug=slug)
    liked = bp.id in _get_liked_posts_from_cookie(request)
    comment_form_class = (
        LoggedInCommentForm if current_user.is_authenticated else NotLoggedInCommentForm
    )
    response = templates.TemplateResponse(
        "blog/read_post.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.LOGIN_FORM: LoginForm(redirect_url=str(request.url)),
            BLOG_POST: bp,
            LIKED: liked,
            COMMENT_FORM: comment_form_class(),
        },
    )
    web_user_handlers.set_guest_user_id_cookie(guest_id=current_user.guest_id, response=response)
    return response


@router.post("/blog/{bp_id}/like", response_model=None)
async def like_blog_post(request: Request, db: DBSession, bp_id: int) -> _TemplateResponse:
    """Like or unlike a blog post and set a cookie to remember it."""
    with db.begin():
        bp = blog_handler.get_bp_from_id(db=db, bp_id=bp_id, for_update=True)
        liked_posts = _get_liked_posts_from_cookie(request)
        liked = bp.id in liked_posts
        blog_handler.toggle_blog_post_like(db=db, bp=bp, like=not liked)
    db.refresh(bp)

    response = templates.TemplateResponse(
        "blog/partials/like_button.html",
        {
            constants.REQUEST: request,
            LIKED: not liked,
            BLOG_POST: bp,
        },
    )

    if liked:
        liked_posts.remove(bp.id)
    else:
        liked_posts.add(bp.id)
    liked_posts_str = ",".join(str(id_) for id_ in sorted(liked_posts))
    response.set_cookie(
        LIKED_POSTS_COOKIE, liked_posts_str, max_age=constants.ONE_YEAR_IN_SECONDS, httponly=True
    )
    return response


class LoggedInCommentForm(Form):
    """Form for creating a comment when logged in."""

    content = TextAreaField(
        "Comment (markdown enabled)",
        description="Comment (2000 characters max, markdown enabled)",
        validators=[validators.DataRequired(), validators.Length(min=1, max=2000)],
    )


class EditCommentForm(LoggedInCommentForm):
    """Form for editing a comment when logged in."""

    name = StringField(
        "Display name",
        description="Anonymous Cat... (100 chars max)",
        validators=[validators.Optional(), validators.Length(min=1, max=100)],
    )


class NotLoggedInCommentForm(LoggedInCommentForm):
    """Form for creating a comment when not logged in."""

    check_me = HiddenField("Honey Pot Field", validators=[custom_validators.is_value(value="")])
    not_robot = BooleanField(
        "I am not a robot",
        default=False,
        validators=[custom_validators.is_value(value=True, error_msg="No robots allowed!")],
    )
    name = StringField(
        "Display name",
        description="Anonymous Cat... (100 chars max)",
        validators=[validators.DataRequired(), validators.Length(min=1, max=100)],
    )
    email = EmailField(
        "Email (optional—for reply messages)",
        description="awesome@email.com",
        validators=[validators.Optional(), validators.Email()],
    )


@router.get("/blog/get-comment/{comment_id}", response_model=None)
async def get_comment(
    request: Request, db: DBSession, comment_id: int, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Return a comment. Called when canceling a comment edit."""
    comment = blog_handler.get_comment_from_id(db=db, comment_id=comment_id)
    return templates.TemplateResponse(
        COMMENT_TEMPLATE,
        {constants.REQUEST: request, constants.CURRENT_USER: current_user, "comment": comment},
    )


@router.get("/blog/comment/{comment_id}", response_model=None)
async def comment_edit_get(
    request: Request, db: DBSession, comment_id: int, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Return page partial to edit a comment."""
    comment = blog_handler.get_comment_from_id(db=db, comment_id=comment_id)
    if not blog_handler.can_edit_comment(current_user=current_user, comment=comment):
        return templates.TemplateResponse(
            COMMENT_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.MESSAGE: FormErrorMessage(text="You can't edit this comment."),
                "comment": comment,
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
    name = comment.name or comment.user.full_name
    form = NotLoggedInCommentForm.load({"name": name, "content": comment.md_content})
    return templates.TemplateResponse(
        COMMENT_FORM_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            COMMENT_FORM: form,
            BLOG_POST: comment.blog_post,
            "is_edit": True,
            "comment_preview": comment,
            "comment_form_id": f"comment-form-{comment.id}",
            "preview_comment_id": f"preview-comment-{comment.id}",
        },
    )


@router.post("/blog/{bp_id}/comment-preview", response_model=None)
async def comment_post_preview(
    request: Request, bp_id: int, current_user: LoggedInUserOptional
) -> _TemplateResponse | HTMLResponse:
    """Preview a comment."""
    form_data = await request.form()
    form_data_dict = dict(form_data)

    comment_form_class = (
        LoggedInCommentForm if current_user.is_authenticated else NotLoggedInCommentForm
    )
    form = comment_form_class.load(form_data)
    form.validate()
    if form.content.errors:
        return HTMLResponse()
    if current_user.is_authenticated:
        assert hasattr(current_user, "full_name")  # noqa: S101 (assert-used)
        form_data_dict["name"] = current_user.full_name or current_user.username
    user_id = current_user.id if current_user.is_authenticated else None
    try:
        input_data = blog_handler.SaveCommentInput(**form_data_dict, user_id=user_id, bp_id=bp_id)
    except ValidationError:
        return HTMLResponse()
    comment = blog_handler.generate_comment(input_data)
    return templates.TemplateResponse(
        COMMENT_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            "comment": comment,
            "comment_user": current_user if current_user.is_authenticated else None,
            "is_preview": True,
        },
    )


@router.post("/blog/{bp_id}/comment", response_model=None)
async def comment_blog_post(
    request: Request, db: DBSession, bp_id: int, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Comment on a blog post."""
    form_data = await request.form()
    form_data_dict = dict(form_data)

    comment_form_class = (
        LoggedInCommentForm if current_user.is_authenticated else NotLoggedInCommentForm
    )
    form = comment_form_class.load(form_data)
    bp = blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    liked = bp.id in _get_liked_posts_from_cookie(request)
    if current_user.is_authenticated:
        assert hasattr(current_user, "full_name")  # noqa: S101 (assert-used)
        form_data_dict["name"] = current_user.full_name or current_user.username
    user_id = current_user.id if current_user.is_authenticated else None
    try:
        input_data = blog_handler.SaveCommentInput(
            **form_data_dict, guest_id=current_user.guest_id, user_id=user_id, bp_id=bp_id
        )
    except ValidationError:
        FlashMessage(
            title=ERROR_SAVING_COMMENT,
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENTS_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                COMMENT_FORM: form,
                constants.MESSAGE: FormErrorMessage(),
                BLOG_POST: bp,
                LIKED: liked,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    comment = blog_handler.generate_comment(input_data)
    if not form.validate():
        form_error_msg = (
            "No robots allowed!" if form.check_me.errors else DEFAULT_FORM_ERROR_MESSAGE
        )
        FlashMessage(
            title=ERROR_SAVING_COMMENT,
            text=form_error_msg,
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENTS_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                COMMENT_FORM: form,
                constants.MESSAGE: FormErrorMessage(text=form_error_msg),
                BLOG_POST: bp,
                "comment_preview": comment,
                LIKED: liked,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    saved_comment_response = blog_handler.save_new_comment(db, input_data)

    if not saved_comment_response.success:
        for error_field, error_msg in saved_comment_response.field_errors.items():
            form[error_field].errors.extend(error_msg)
        FlashMessage(
            title=ERROR_SAVING_COMMENT,
            text=saved_comment_response.err_msg,
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENTS_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.FORM: form,
                constants.MESSAGE: FormErrorMessage(text=saved_comment_response.err_msg),
                BLOG_POST: bp,
                "comment_preview": comment,
                LIKED: liked,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    db.refresh(bp)
    FlashMessage(
        title="Comment saved!",
        text="Find it above the form.",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    response = templates.TemplateResponse(
        COMMENTS_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            COMMENT_FORM: comment_form_class(),
            BLOG_POST: bp,
            LIKED: liked,
        },
    )
    web_user_handlers.set_guest_user_id_cookie(guest_id=current_user.guest_id, response=response)
    return response


@router.post("/blog/comment/{comment_id}", response_model=None)
async def edit_comment(
    request: Request,
    db: DBSession,
    comment_id: int,
    current_user: LoggedInUserOptional,
) -> _TemplateResponse:
    """Edit a comment."""
    comment = blog_handler.get_comment_from_id(db=db, comment_id=comment_id)
    if not blog_handler.can_edit_comment(current_user=current_user, comment=comment):
        FlashMessage(
            title="Error editing comment",
            text="You don't have permission to edit this comment.",
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENT_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                "comment": comment,
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    form_data = await request.form()
    md_content = form_data.get("content")
    if not (md_content and isinstance(md_content, str)):
        FlashMessage(
            title="Error editing comment",
            text="No content provided.",
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENT_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                "comment": comment,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        comment = blog_handler.update_existing_comment(
            db=db, comment=comment, md_content=md_content, current_user=current_user
        )
    except Exception:
        logger.exception("Error updating comment")
        FlashMessage(
            title="Error updating comment",
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENT_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                "comment": comment,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    FlashMessage(
        title="Comment updated!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return templates.TemplateResponse(
        COMMENT_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            "comment": comment,
        },
    )


@router.delete("/blog/comment/{comment_id}", response_model=None)
def delete_comment(
    request: Request,
    db: DBSession,
    comment_id: int,
    current_user: LoggedInUserOptional,
) -> _TemplateResponse:
    """Delete a comment."""
    response = blog_handler.delete_comment(db=db, comment_id=comment_id, current_user=current_user)
    if not response.success:
        FlashMessage(
            title="Error deleting comment",
            text=response.err_msg,
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            COMMENT_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.MESSAGE: FormErrorMessage(text=response.err_msg),
                "comment": response.comment,
            },
            status_code=response.status_code,
        )
    FlashMessage(
        title="Comment deleted",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return templates.TemplateResponse(
        "blog/partials/comment_deleted.html", {constants.REQUEST: request}
    )


class BlogPostMediaForm(Form):
    """Form for uploading media for a blog post."""

    name = StringField(
        "Name (title)", description="A dog dancing", validators=[validators.DataRequired()]
    )
    media = FileField(
        "Upload media file",
        validators=[
            validators.DataRequired(),
            custom_validators.is_allowed_extension(
                ["jpg", "jpeg", "png", "gif", "webp", "svg", "mp4", "webm"]
            ),
        ],
    )


@router.get("/blog/{bp_id}/edit", response_model=None)
@requires_permission(Action.EDIT_BP)
async def edit_bp_get(
    request: Request, current_user: LoggedInUser, db: DBSession, bp_id: int
) -> _TemplateResponse:
    """Return page to edit a blog post."""
    bp = blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    form = BlogPostForm.load(
        {
            "is_new": False,
            "title": bp.title,
            "tags": ", ".join([tag.tag for tag in bp.tags]),
            "can_comment": bp.can_comment,
            "is_published": bp.is_published,
            "description": bp.markdown_description,
            "content": bp.markdown_content,
            "thumbnail_url": bp.thumbnail_location or "",
        }
    )

    return templates.TemplateResponse(
        EDIT_BP_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.FORM: form,
            MEDIA_FORM: BlogPostMediaForm(),
            BLOG_POST: bp,
        },
    )


@router.post("/blog/{bp_id}/edit", response_model=None)
@requires_permission(Action.EDIT_BP)
async def edit_bp_post(
    request: Request, current_user: LoggedInUser, db: DBSession, bp_id: int
) -> _TemplateResponse | RedirectResponse:
    """Return page to edit a blog post."""
    form_data = await request.form()
    form = BlogPostForm.load(form_data)
    if not form.validate():
        return templates.TemplateResponse(
            EDIT_BP_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.FORM: form,
                constants.MESSAGE: FormErrorMessage(),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    bp = blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    input_data = blog_handler.SaveBlogInput(**form.data, existing_bp=bp)
    response = blog_handler.save_blog_post(db, input_data)
    if not response.success or not response.blog_post:
        for error_field, error_msg in response.field_errors.items():
            form[error_field].errors.extend(error_msg)
        return templates.TemplateResponse(
            EDIT_BP_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.FORM: form,
                constants.MESSAGE: FormErrorMessage(text=response.err_msg),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    FlashMessage(
        title="Blog Post Updated!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        url=request.url_for("html:edit_bp_get", bp_id=response.blog_post.id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/blog/live-edit", response_model=None)
@requires_permission(Action.EDIT_BP)
async def edit_bp_live_update(
    request: Request, current_user: LoggedInUser
) -> _TemplateResponse | str:
    """Return page to edit a blog post."""
    form_data = await request.form()
    form = BlogPostForm.load(form_data)
    if not form.validate():
        return f"Invalid form data. Errors: {form.errors}"
    input_data = blog_handler.SaveBlogInput(**form.data)
    bp = blog_handler.set_new_bp_fields(data=input_data)
    return templates.TemplateResponse(
        "blog/partials/edit_preview.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            BLOG_POST: bp,
        },
    )


@router.post("/blog/{bp_id}/upload-media", response_model=None)
@requires_permission(Action.EDIT_BP)
async def upload_blog_post_media(
    request: Request,
    current_user: LoggedInUser,
    db: DBSession,
    bp_id: int,
    media: UploadFile | None = None,
) -> _TemplateResponse:
    """Upload media for a blog post."""
    form_data = await request.form()
    form_data_dict = {
        "name": form_data["name"],
        "media": media,
    }
    form = BlogPostMediaForm.load(form_data_dict)
    bp = blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    if not form.validate():
        return templates.TemplateResponse(
            UPLOAD_MEDIA_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.CURRENT_USER: current_user,
                constants.FORM: form,
                BLOG_POST: bp,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    bp = blog_handler.save_media_for_blog_post(
        db=db,
        blog_post=bp,
        name=form.name.data,
        media=form.media.data,
    )
    return templates.TemplateResponse(
        UPLOAD_MEDIA_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.FORM: BlogPostMediaForm(),
            BLOG_POST: bp,
        },
    )


@router.patch("/blog/{bp_id}/reorder-media/{media_id}", response_model=None)
@requires_permission(Action.EDIT_BP)
async def reorder_bp_media(
    request: Request,
    current_user: LoggedInUser,
    db: DBSession,
    bp_id: int,
    media_id: int,
) -> _TemplateResponse:
    """Update media position number."""
    form_data = await request.form()
    position_str = form_data.get("position", "")
    if position_str == "":
        position = None
    elif str(position_str).removeprefix("-").isdigit():
        position = int(str(position_str))
    else:
        FlashMessage(
            title="Error reordering media",
            text="Invalid position",
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            FLASH_ERRORS_TEMPLATE,
            {constants.REQUEST: request},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    bp = blog_handler.reorder_media_for_blog_post(
        db=db,
        media_id=media_id,
        bp_id=bp_id,
        position=position,
    )
    return templates.TemplateResponse(
        LIST_MEDIA_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            BLOG_POST: bp,
        },
    )


@router.delete("/blog/{bp_id}/upload-media/{media_id}", response_model=None)
@requires_permission(Action.EDIT_BP)
async def delete_blog_post_media(
    request: Request,
    current_user: LoggedInUser,
    db: DBSession,
    bp_id: int,
    media_id: int,
) -> _TemplateResponse:
    """Delete a blog post."""
    bp = blog_handler.delete_media_from_blog_post(
        db=db,
        media_id=media_id,
        bp_id=bp_id,
    )
    return templates.TemplateResponse(
        UPLOAD_MEDIA_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.FORM: BlogPostMediaForm(),
            BLOG_POST: bp,
        },
    )
