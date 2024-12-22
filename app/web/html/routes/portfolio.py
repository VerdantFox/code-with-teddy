"""landing: HTML routes for landing."""

import sentry_sdk
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import _TemplateResponse

from app import constants
from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["portfolio"])


@router.get("/", response_model=None)
async def about(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing (about) page."""
    return templates.TemplateResponse(
        "main/about/about.html",
        {constants.REQUEST: request},
    )


@router.get("/projects", response_model=None)
async def projects(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio projects page."""
    return templates.TemplateResponse(
        "main/projects/projects.html",
        {constants.REQUEST: request},
    )


@router.get("/experience", response_model=None)
async def experience(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio experience page."""
    return templates.TemplateResponse(
        "main/experience/experience.html",
        {constants.REQUEST: request},
    )


@router.get("/healthcheck", response_model=None)
async def healthcheck(
    request: Request,  # noqa: ARG001 (unused argument)
) -> HTMLResponse:
    """Return the portfolio healthcheck page."""
    scope = sentry_sdk.get_current_scope()
    if scope.transaction:
        scope.transaction.sampled = False
    return HTMLResponse(content="ok")
