"""landing: HTML routes for landing."""

from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse

from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["blog"])


@router.get("/blog", response_model=None)
async def list_blog_posts(
    request: Request,
) -> _TemplateResponse:
    """Return the blog list page."""
    return templates.TemplateResponse(
        "main/blog/list/blog_list.html",
        {"request": request},
    )
