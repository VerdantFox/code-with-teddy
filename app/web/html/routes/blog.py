"""landing: HTML routes for landing."""

from logging import getLogger

from fastapi import APIRouter, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from starlette.templating import _TemplateResponse
from wtforms import (
    FileField,
    StringField,
    TextAreaField,
    validators,
)

from app import constants
from app.datastore.database import DBSession
from app.permissions import Action, requires_permission
from app.services.blog import blog_handler
from app.web.auth import LoggedInUser, LoggedInUserOptional
from app.web.html.const import templates
from app.web.html.flash_messages import FlashCategory, FlashMessage, FormErrorMessage
from app.web.html.routes.users import LoginForm
from app.web.html.wtform_utils import Form
from app.web.html.wtform_utils.wtform_fields import BooleanField

# ----------- Routers -----------
router = APIRouter(tags=["blog"])

logger = getLogger(__name__)
BLOG_POST = "blog_post"
EDIT_BP_TEMPLATE = "blog/edit_post.html"
UPLOAD_MEDIA_TEMPLATE = "blog/partials/edit_post_media_form.html"
MEDIA_FORM = "media_form"


@router.get("/blog", response_model=None)
async def list_blog_posts(
    request: Request, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Return the blog list page."""
    return templates.TemplateResponse(
        "blog/list_posts.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.LOGIN_FORM: LoginForm(redirect_url=str(request.url)),
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
                constants.MESSAGE: FormErrorMessage(msg=response.err_msg),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    FlashMessage(
        msg="Blog Post Saved!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        url=request.url_for("html:edit_bp_get", bp_id=response.blog_post.id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/blog/{slug}", response_model=None)
async def read_blog_post(
    request: Request, current_user: LoggedInUserOptional, db: DBSession, slug: str
) -> _TemplateResponse:
    """Return page to read a blog post.

    NOTE: This route needs to be after the create_bp_get route,
    otherwise it will match.
    """
    bp = blog_handler.get_bp_from_slug(db=db, slug=slug)
    return templates.TemplateResponse(
        "blog/read_post.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.LOGIN_FORM: LoginForm(redirect_url=str(request.url)),
            BLOG_POST: bp,
        },
    )


class BlogPostMediaForm(Form):
    """Form for uploading media for a blog post."""

    name = StringField(
        "Name (title)", description="A dog dancing", validators=[validators.DataRequired()]
    )
    media = FileField("Upload media file", validators=[validators.DataRequired()])


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
                constants.MESSAGE: FormErrorMessage(msg=response.err_msg),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    FlashMessage(
        msg="Blog Post Updated!",
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
