"""projects: HTML routes for projects."""

from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse

from app import constants
from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["projects"])


@router.get("/twisted-towers", response_model=None)
async def twisted_towers(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing (about) page."""
    return templates.TemplateResponse(
        "projects/twisted_towers.html",
        {constants.REQUEST: request},
    )
