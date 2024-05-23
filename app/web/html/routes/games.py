"""games: routes for games."""

from fastapi import APIRouter, Request
from starlette.templating import _TemplateResponse

from app import constants
from app.web.html.const import templates

# ----------- Routers -----------
router = APIRouter(tags=["games"])


@router.get("/connect-4", response_model=None)
async def connect_4(request: Request) -> _TemplateResponse:
    """Return the connect 4 game page."""
    return templates.TemplateResponse("projects/connect4.html", {constants.REQUEST: request})
