"""landing: HTML routes for landing."""

from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse

from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["landing"])

# headers = {  noqa: ERA001 (commented-out-code)
#     "HX-Replace-Url": str(request.url_for("html:landing")),
#     "HX-Refresh": "true",
# }  noqa: ERA001 (commented-out-code)


@router.get("/", response_model=None)
async def landing(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing (about) page."""
    return templates.TemplateResponse(
        "main/about/about.html",
        {"request": request},
    )


@router.get("/projects", response_model=None)
async def projects(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing page."""
    return templates.TemplateResponse(
        "main/projects/projects.html",
        {"request": request},
    )


@router.get("/experience", response_model=None)
async def experience(
    request: Request,
) -> _TemplateResponse:
    """Return the portfolio landing page."""
    return templates.TemplateResponse(
        "main/experience/experience.html",
        {"request": request},
    )
