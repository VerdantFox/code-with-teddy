"""landing: HTML routes for landing."""

from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse

from app import constants
from app.web.auth import LoggedInUser, LoggedInUserOptional
from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["blog"])


@router.get("/blog", response_model=None)
async def list_blog_posts(
    request: Request, current_user: LoggedInUserOptional
) -> _TemplateResponse:
    """Return the blog list page."""
    return templates.TemplateResponse(
        "main/blog/list_posts.html",
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )


@router.get("/blog/{slug}", response_model=None)
async def read_blog_post(
    request: Request,
    current_user: LoggedInUserOptional,
    slug: str,  # noqa: ARG001 (unused-argument)
) -> _TemplateResponse:
    """Return page to read a blog post."""
    return templates.TemplateResponse(
        "main/blog/read_post.html",
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )


@router.get("/blog/create", response_model=None)
async def create_blog_post(request: Request, current_user: LoggedInUser) -> _TemplateResponse:
    """Return page to create a blog post."""
    return templates.TemplateResponse(
        "main/blog/edit_post.html",
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )


@router.get("/blog/{bp_id}/edit", response_model=None)
async def edit_blog_post(
    request: Request,
    current_user: LoggedInUser,
    bp_id: int,  # noqa: ARG001 (unused-argument)
) -> _TemplateResponse:
    """Return page to edit a blog post."""
    return templates.TemplateResponse(
        "main/blog/edit_post.html",
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )


@router.get("/blog/{bp_id}/upload-media", response_model=None)
async def upload_media_for_blog_post(
    request: Request,
    current_user: LoggedInUser,
    bp_id: int,  # noqa: ARG001 (unused-argument)
) -> _TemplateResponse:
    """Return page to edit a blog post."""
    return templates.TemplateResponse(
        "main/blog/upload_media.html",
        {constants.REQUEST: request, constants.CURRENT_USER: current_user},
    )
