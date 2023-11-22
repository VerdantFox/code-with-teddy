"""flash_messages: Flash messages for the HTML web package."""
from enum import Enum
from typing import cast

from fastapi import Request
from pydantic import BaseModel

MESSAGES = "_messages"


class FlashCategory(str, Enum):
    """Categories for flash messages.

    Categories are used to style the flash message.
    """

    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"


class FlashMessage(BaseModel):
    """Message to be flashed to the user."""

    msg: str
    category: FlashCategory = FlashCategory.INFO
    timeout: int | None = None

    def flash(self, request: Request) -> None:
        """Add this message to the session."""
        if MESSAGES not in request.session:
            request.session[MESSAGES] = []
        request.session[MESSAGES].append(self.model_dump())


def get_flashed_messages(request: Request) -> list[FlashMessage]:
    """Get flashed messages from the session."""
    message = cast(list[dict], request.session.pop(MESSAGES, []))
    return [FlashMessage(**msg) for msg in message]
