"""landing: HTML routes for landing."""

from logging import getLogger

import sqlalchemy
from fastapi import APIRouter, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from starlette.templating import _TemplateResponse
from wtforms import (
    EmailField,
    FileField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
    validators,
)

from app import constants
from app.datastore.database import DBSession
from app.permissions import Action, requires_permission
from app.services.blog import blog_handler
from app.web import errors
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
LIST_POSTS_FULL_TEMPLATE = "blog/list_posts.html"
LIST_POSTS_FORM_TEMPLATE = "blog/partials/list_posts_form.html"
LISTED_POSTS_TEMPLATE = "blog/partials/listed_posts.html"
EDIT_BP_TEMPLATE = "blog/edit_post.html"
UPLOAD_MEDIA_TEMPLATE = "blog/partials/edit_post_media_form.html"
LIST_MEDIA_TEMPLATE = "blog/partials/list_post_media.html"
FLASH_ERRORS_TEMPLATE = "shared/partials/flash_error_messages.html"
COMMENTS_TEMPLATE = "blog/partials/comments.html"
COMMENT_TEMPLATE = "blog/partials/comment.html"
COMMENT_FORM_TEMPLATE = "blog/partials/comment_form.html"
MANAGE_SERIES_TEMPLATE = "blog/manage_series.html"
LIST_SERIES_TEMPLATE = "blog/partials/list_series.html"
SINGLE_SERIES_TEMPLATE = "blog/partials/single_series.html"
ADD_SERIES_FORM_TEMPLATE = "blog/partials/add_series_form.html"
DELETED_SERIES_TEMPLATE = "blog/partials/deleted_series.html"

MEDIA_FORM = "media_form"
COMMENT_FORM = "comment_form"
LIKED_POSTS_COOKIE = "liked_posts"  # Sets a cookie with a list of liked posts, by id
VIEWED_POSTS_COOKIE = "viewed_posts"  # Sets a cookie with a list of viewed posts, by id
ERROR_SAVING_COMMENT = "Error saving comment"


class SearchForm(Form):
    """Form for searching blog posts."""

    search = StringField(
        "Search", description="Search blog posts", validators=[validators.optional()]
    )
    # Advanced search fields
    tags = StringField(
        "Tags (comma separated)",
        description="python, fastapi, web",
        validators=[validators.optional()],
    )
    order_by = SelectField(
        "Order by",
        choices=[
            ("created_timestamp", "Published date"),
            ("title", "Title"),
            ("read_mins", "Read time"),
            ("views", "Views"),
            ("likes", "Likes"),
        ],
        default="created_timestamp",
    )
    asc = BooleanField("Ascending", default=False)
    results_per_page = SelectField(
        "Results per page",
        choices=[(1, "1"), (2, "2"), (5, "5"), (10, "10"), (20, "20"), (50, "50"), (100, "100")],
        default=10,
        coerce=int,
    )
    page = IntegerField("Page", default=1, validators=[validators.optional()])


@router.get("/blog", response_model=None)
async def list_blog_posts(
    request: Request,
    current_user: LoggedInUserOptional,
    db: DBSession,
) -> _TemplateResponse:
    """Return the blog list page."""
    is_form_request = request.headers.get("hx-target") == "blog-post-list"
    params = dict(request.query_params)
    form = SearchForm.load(params)
    status_code = status.HTTP_200_OK
    if not form.validate():
        template = LIST_POSTS_FORM_TEMPLATE if is_form_request else LIST_POSTS_FULL_TEMPLATE
        FlashMessage(
            title="Error searching blog posts",
            text="See errors in form",
            category=FlashCategory.ERROR,
        ).flash(request)
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    try:
        paginator: blog_handler.Paginator | None = await blog_handler.get_blog_posts(
            db=db,
            can_see_unpublished=current_user.has_permission(Action.READ_UNPUBLISHED_BP),
            search=form.search.data,
            tags=form.tags.data,
            order_by_field=form.order_by.data,
            asc=form.asc.data,
            results_per_page=form.results_per_page.data,
            page=form.page.data,
        )
    except AttributeError:
        FlashMessage(
            title="Error retrieving blog posts",
            category=FlashCategory.ERROR,
        ).flash(request)
        paginator = None
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    if paginator:
        form.page.data = paginator.current_page
    template = LISTED_POSTS_TEMPLATE if is_form_request else LIST_POSTS_FULL_TEMPLATE

    return templates.TemplateResponse(
        template,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.LOGIN_FORM: LoginForm(redirect_url=str(request.url)),
            constants.FORM: form,
            "paginator": paginator,
        },
        status_code=status_code,
    )


class BlogPostForm(Form):
    """Form for creating and editing blog posts."""

    is_new = BooleanField("Is new", default=False)
    title = StringField("Title", description="My cool post", validators=[validators.Length(min=1)])
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
            validators.Length(max=2000),
        ],
    )
    series_name = IntegerField(
        "Series ID",
        description="Series ID (optional)",
        validators=[validators.optional()],
    )
    series_position = IntegerField(
        "Series Position",
        description="99 (optional)",
        validators=[validators.optional()],
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
    response = await blog_handler.save_blog_post(db, input_data)
    if not response.success or not response.blog_post:
        for error_field, error_msg in response.field_errors.items():
            form[error_field].errors.extend(error_msg)

        # If there is a database error, `current_user` goes stale and needs refreshing.
        await db.refresh(current_user)
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


class SeriesSearchForm(Form):
    """Form for searching blog post series."""

    search = StringField(
        "Search", description="Search blog post series", validators=[validators.optional()]
    )


class SeriesUpdateForm(Form):
    """Form for updating a blog post series."""

    name = StringField("Name", description="My new series", validators=[validators.Length(min=1)])
    description = StringField(
        "Description",
        description="Short plain text description",
        validators=[validators.optional()],
    )


@router.get("/blog/series", response_model=None)
@requires_permission(Action.EDIT_BP)
async def get_manage_series(
    request: Request, current_user: LoggedInUser, db: DBSession
) -> _TemplateResponse:
    """Return page to manage blog post series."""
    is_form_request = request.headers.get("hx-target") == "series-list"
    template = LIST_SERIES_TEMPLATE if is_form_request else MANAGE_SERIES_TEMPLATE
    params = dict(request.query_params)
    search_form = SeriesSearchForm.load(params)
    series_list = await blog_handler.get_all_series(db=db, search=search_form.search.data)
    return templates.TemplateResponse(
        template,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            "search_form": search_form,
            "series_list": series_list,
            "series_update_form": SeriesUpdateForm,
        },
    )


@router.post("/blog/series", response_model=None)
@requires_permission(Action.EDIT_BP)
async def create_series(
    request: Request,
    current_user: LoggedInUser,  # noqa: ARG001
    db: DBSession,
) -> _TemplateResponse:
    """Create a blog post series."""
    form_data = await request.form()
    form = SeriesUpdateForm.load(form_data)
    err_msg_title = "Error creating series"
    if not form.validate():
        FlashMessage(
            title=err_msg_title,
            text="See errors in form",
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            MANAGE_SERIES_TEMPLATE,
            {
                constants.REQUEST: request,
                "form": form,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        series = await blog_handler.create_series(
            db=db, name=form.name.data, description=form.description.data
        )
    except sqlalchemy.exc.IntegrityError:
        logger.exception(err_msg_title)
        FlashMessage(
            title=err_msg_title,
            text="Name already exists.",
            category=FlashCategory.ERROR,
            timeout=20,
        ).flash(request)
        return templates.TemplateResponse(
            ADD_SERIES_FORM_TEMPLATE,
            {
                constants.REQUEST: request,
                "form": form,
                "series_update_form": SeriesUpdateForm,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    FlashMessage(
        title="Series Created!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return templates.TemplateResponse(
        SINGLE_SERIES_TEMPLATE,
        {
            constants.REQUEST: request,
            "form": SeriesUpdateForm(name=series.name, description=series.description),
            "series": series,
            "series_update_form": SeriesUpdateForm,
            "add_series": True,
        },
    )


@router.patch("/blog/series/{series_id}", response_model=None)
@requires_permission(Action.EDIT_BP)
async def update_series(
    request: Request,
    current_user: LoggedInUser,  # noqa: ARG001
    db: DBSession,
    series_id: int,
) -> _TemplateResponse:
    """Update a blog post series."""
    form_data = await request.form()
    form = SeriesUpdateForm.load(form_data)
    series = await blog_handler.get_series_from_id(db=db, series_id=series_id)
    if not form.validate():
        FlashMessage(
            title="Error updating series",
            text="See errors in form",
            category=FlashCategory.ERROR,
        ).flash(request)
        return templates.TemplateResponse(
            SINGLE_SERIES_TEMPLATE,
            {
                constants.REQUEST: request,
                "form": form,
                "series": series,
                "series_update_form": SeriesUpdateForm,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    series = await blog_handler.update_series(
        db=db, series=series, name=form.name.data, description=form.description.data
    )
    FlashMessage(
        title="Series Updated!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return templates.TemplateResponse(
        SINGLE_SERIES_TEMPLATE,
        {
            constants.REQUEST: request,
            "form": SeriesUpdateForm(name=series.name, description=series.description),
            "series": series,
            "series_update_form": SeriesUpdateForm,
        },
    )


@router.delete("/blog/series/{series_id}", response_model=None)
@requires_permission(Action.EDIT_BP)
async def delete_series(
    request: Request,
    current_user: LoggedInUser,  # noqa: ARG001
    db: DBSession,
    series_id: int,
) -> _TemplateResponse:
    """Delete a blog post series."""
    try:
        await blog_handler.delete_series(db=db, series_id=series_id)
    except (sqlalchemy.exc.IntegrityError, sqlalchemy.exc.PendingRollbackError) as e:
        logger.exception("Error deleting series")
        FlashMessage(
            title="Error deleting series",
            text=str(e),
            category=FlashCategory.ERROR,
        ).flash(request)
        message = str(e)
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        FlashMessage(
            title="Series Deleted!",
            category=FlashCategory.SUCCESS,
        ).flash(request)
        message = "Series deleted."
        status_code = status.HTTP_200_OK
    return templates.TemplateResponse(
        DELETED_SERIES_TEMPLATE,
        {
            constants.REQUEST: request,
            "message": message,
        },
        status_code=status_code,
    )


def _get_liked_posts_from_cookie(request: Request) -> set[int]:
    """Get the liked posts from the cookie."""
    return {int(id_) for id_ in request.cookies.get(LIKED_POSTS_COOKIE, "").split(",") if id_}


def _get_viewed_posts_from_cookie(request: Request) -> set[int]:
    """Get the viewed posts from the cookie."""
    return {int(id_) for id_ in request.cookies.get(VIEWED_POSTS_COOKIE, "").split(",") if id_}


@router.get("/blog/{slug}", response_model=None)
async def read_blog_post(
    request: Request, current_user: LoggedInUserOptional, db: DBSession, slug: str
) -> _TemplateResponse:
    """Return page to read a blog post.

    NOTE: This route needs to be after the create_bp_get route,
    otherwise it will match.
    """
    bp = await blog_handler.get_bp_from_slug(db=db, slug=slug)
    if (not bp.is_published) and (not current_user.has_permission(Action.READ_UNPUBLISHED_BP)):
        raise errors.BlogPostNotFoundError
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


@router.get("/blog/{bp_id}/view", response_model=None)
async def view_blog_post(request: Request, db: DBSession, bp_id: int) -> HTMLResponse:
    """Increment the view count for a blog post."""
    bp = await blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    viewed_posts = _get_viewed_posts_from_cookie(request)
    if bp.id in viewed_posts:
        return HTMLResponse(content=f"{bp.views:,}")
    bp = await blog_handler.increment_bp_views(db=db, bp=bp)
    viewed_posts.add(bp.id)
    viewed_posts_str = ",".join(str(id_) for id_ in sorted(viewed_posts))
    response = HTMLResponse(content=f"{bp.views:,}")
    response.set_cookie(
        VIEWED_POSTS_COOKIE,
        viewed_posts_str,
        max_age=constants.ONE_YEAR_IN_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.post("/blog/{bp_id}/like", response_model=None)
async def like_blog_post(request: Request, db: DBSession, bp_id: int) -> _TemplateResponse:
    """Like or unlike a blog post and set a cookie to remember it."""
    async with db.begin():
        bp = await blog_handler.get_bp_from_id(db=db, bp_id=bp_id, for_update=True)
        liked_posts = _get_liked_posts_from_cookie(request)
        liked = bp.id in liked_posts
        await blog_handler.toggle_blog_post_like(db=db, bp=bp, like=not liked)
    await db.refresh(bp)

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
        LIKED_POSTS_COOKIE,
        liked_posts_str,
        max_age=constants.ONE_YEAR_IN_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


class LoggedInCommentForm(Form):
    """Form for creating a comment when logged in."""

    content = TextAreaField(
        "Comment (markdown enabled)",
        description="Comment (1000 characters max, markdown enabled)",
        validators=[validators.DataRequired(), validators.Length(min=1, max=1000)],
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
        "Email (optional—for replies only)",
        description="awesome@email.com (optional)",
        validators=[validators.Optional(), validators.Email()],
    )


@router.get("/blog/comment/{comment_id}", response_model=None)
async def get_comment(
    request: Request, db: DBSession, comment_id: int, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Return a comment partial. Called when canceling a comment edit."""
    comment = await blog_handler.get_comment_from_id(db=db, comment_id=comment_id)
    await db.refresh(comment)
    return templates.TemplateResponse(
        COMMENT_TEMPLATE,
        {constants.REQUEST: request, constants.CURRENT_USER: current_user, "comment": comment},
    )


@router.get("/blog/comment/{comment_id}/edit", response_model=None)
async def comment_edit_get(
    request: Request, db: DBSession, comment_id: int, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Return page partial to edit a comment."""
    comment = await blog_handler.get_comment_from_id(db=db, comment_id=comment_id)
    if not blog_handler.can_edit_comment(current_user=current_user, comment=comment):
        await db.refresh(comment)
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
    await db.refresh(comment)
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
        assert hasattr(current_user, "full_name")  # noqa: S101 (assert-used for mypy)
        form_data_dict["name"] = current_user.full_name or current_user.username
    user_id = current_user.id if current_user.is_authenticated else None
    try:
        input_data = blog_handler.CommentInputPreview(
            **form_data_dict, user_id=user_id, bp_id=bp_id
        )
    except ValidationError:  # pragma: no cover (not sure this is reachable)
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
    bp = await blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    liked = bp.id in _get_liked_posts_from_cookie(request)

    if (not bp.can_comment) and (not current_user.is_admin):
        FlashMessage(
            title="Error saving comment",
            text="Comments are not allowed on this post.",
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
    if current_user.is_authenticated:
        assert hasattr(current_user, "full_name")  # noqa: S101 (assert-used mypy)
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
    await blog_handler.save_new_comment(db, input_data)
    await db.refresh(bp)
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


@router.patch("/blog/comment/{comment_id}", response_model=None)
async def comment_edit_patch(
    request: Request,
    db: DBSession,
    comment_id: int,
    current_user: LoggedInUserOptional,
) -> _TemplateResponse:
    """Edit a comment."""
    comment = await blog_handler.get_comment_from_id(db=db, comment_id=comment_id)
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
        comment = await blog_handler.update_existing_comment(
            db=db, comment=comment, md_content=md_content, current_user=current_user
        )
    except Exception:  # pragma: no cover (not sure this is reachable with proper db setup)
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
    await db.refresh(comment)
    return templates.TemplateResponse(
        COMMENT_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            "comment": comment,
        },
    )


@router.delete("/blog/comment/{comment_id}", response_model=None)
async def delete_comment(
    request: Request,
    db: DBSession,
    comment_id: int,
    current_user: LoggedInUserOptional,
) -> _TemplateResponse:
    """Delete a comment."""
    response = await blog_handler.delete_comment(
        db=db, comment_id=comment_id, current_user=current_user
    )
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
    bp = await blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
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
    bp = await blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
    input_data = blog_handler.SaveBlogInput(**form.data, existing_bp=bp)
    response = await blog_handler.save_blog_post(db, input_data)
    if not response.success or not response.blog_post:
        for error_field, error_msg in response.field_errors.items():
            form[error_field].errors.extend(error_msg)
        await db.refresh(current_user)
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
    bp = await blog_handler.set_new_bp_fields(data=input_data)
    return templates.TemplateResponse(
        "blog/partials/edit_preview.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            BLOG_POST: bp,
        },
    )


@router.post("/blog/{bp_id}/media", response_model=None)
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
        "name": form_data.get("name"),
        "media": media,
    }
    form = BlogPostMediaForm.load(form_data_dict)
    bp = await blog_handler.get_bp_from_id(db=db, bp_id=bp_id)
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

    bp = await blog_handler.save_media_for_blog_post(
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


@router.patch("/blog/{bp_id}/media/{media_id}", response_model=None)
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
    bp = await blog_handler.reorder_media_for_blog_post(
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


@router.delete("/blog/{bp_id}/media/{media_id}", response_model=None)
@requires_permission(Action.EDIT_BP)
async def delete_blog_post_media(
    request: Request,
    current_user: LoggedInUser,
    db: DBSession,
    bp_id: int,
    media_id: int,
) -> _TemplateResponse:
    """Delete a blog post."""
    bp = await blog_handler.delete_media_from_blog_post(
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
