"""landing: HTML routes for landing."""

import aiocache
from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse

from app import constants
from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["landing"])


@router.get("/", response_model=None)
@aiocache.cached(key="constant")
async def about(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing (about) page."""
    return templates.TemplateResponse(
        "main/about/about.html",
        {constants.REQUEST: request},
    )


@router.get("/projects", response_model=None)
@aiocache.cached(key="constant")
async def projects(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing page."""
    return templates.TemplateResponse(
        "main/projects/projects.html",
        {constants.REQUEST: request},
    )


@router.get("/experience", response_model=None)
@aiocache.cached(key="constant")
async def experience(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing page."""
    return templates.TemplateResponse(
        "main/experience/experience.html",
        {constants.REQUEST: request},
    )
