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
    """Return the Twisted Towers project page."""
    return templates.TemplateResponse(
        "projects/twisted_towers.html",
        {constants.REQUEST: request},
    )


@router.get("/moth-hunt", response_model=None)
async def moth_hunt(
    request: Request,
) -> _TemplateResponse:
    """Return the Moth Hunt project page."""
    return templates.TemplateResponse(
        "projects/moth_hunt.html",
        {constants.REQUEST: request},
    )


@router.get("/file-renamer", response_model=None)
async def file_renamer(
    request: Request,
) -> _TemplateResponse:
    """Return the File Renamer project page."""
    return templates.TemplateResponse(
        "projects/file_renamer.html",
        {constants.REQUEST: request},
    )
