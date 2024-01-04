"""landing: HTML routes for landing."""

from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse
from wtforms import (
    BooleanField,
    Form,
    HiddenField,
    StringField,
    TextAreaField,
    validators,
)

from app import constants
from app.permissions import Action, requires_permission
from app.web.auth import LoggedInUser, LoggedInUserOptional
from app.web.html.const import templates
from app.web.html.routes.users import LoginForm

# ----------- Routers -----------
router = APIRouter(tags=["blog"])

EDIT_BP_TEMPLATE = "blog/edit_post.html"
UPLOAD_MEDIA_TEMPLATE = "blog/upload_media.html"


@router.get("/blog", response_model=None)
async def list_blog_posts(
    request: Request,
    current_user: LoggedInUserOptional,
) -> _TemplateResponse:
    """Return the blog list page."""
    login_form = LoginForm(redirect_url=str(request.url))
    return templates.TemplateResponse(
        "blog/list_posts.html",
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            "login_form": login_form,
        },
    )


class BlogPostForm(Form):
    """Form for creating and editing blog posts."""

    is_new = HiddenField("Is new", default=False)
    title = StringField("Title", description="My cool post")
    tags = StringField("Tags", [validators.optional()], description="python, fastapi, web")
    can_comment = BooleanField("Allow Comments", default=True)
    is_published = BooleanField("Publish", default=False)
    description = TextAreaField(
        "Description", description="Short markdown description (couple paragraphs)"
    )
    content = TextAreaField("Content", description="Markdown content (the whole blog post)")


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


@router.get("/blog/create", response_model=None)
@requires_permission(Action.EDIT_BP)
async def create_bp_post(request: Request, current_user: LoggedInUser) -> _TemplateResponse:
    """Post the blog post create form."""
    return templates.TemplateResponse(
        EDIT_BP_TEMPLATE,
        {
            constants.REQUEST: request,
            constants.CURRENT_USER: current_user,
            constants.FORM: BlogPostForm(is_new=True),
        },
    )


@router.get("/blog/{slug}", response_model=None)
async def read_blog_post(
    request: Request,
    current_user: LoggedInUserOptional,
    slug: str,  # noqa: ARG001 (unused-argument)
) -> _TemplateResponse:
    """Return page to read a blog post."""
    return templates.TemplateResponse(
        "blog/read_post.html",
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )


@router.get("/blog/{bp_id}/edit", response_model=None)
@requires_permission(Action.EDIT_BP)
async def edit_blog_post(
    request: Request,
    current_user: LoggedInUser,
    bp_id: int,  # noqa: ARG001 (unused-argument)
) -> _TemplateResponse:
    """Return page to edit a blog post."""
    return templates.TemplateResponse(
        EDIT_BP_TEMPLATE,
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )


@router.get("/blog/{bp_id}/upload-media", response_model=None)
@requires_permission(Action.EDIT_BP)
async def upload_media_for_blog_post(
    request: Request,
    current_user: LoggedInUser,
    bp_id: int,  # noqa: ARG001 (unused-argument)
) -> _TemplateResponse:
    """Return page to edit a blog post."""
    return templates.TemplateResponse(
        UPLOAD_MEDIA_TEMPLATE,
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )
