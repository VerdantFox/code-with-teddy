"""flash_messages: Flash messages for the HTML web package."""
from enum import Enum
from typing import cast

from fastapi import Request
from pydantic import BaseModel

MESSAGES = "_messages"
DEFAULT_FORM_ERROR_MESSAGE = "Invalid form field(s). See errors on form."


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

    title: str | None = None
    text: str | None = None
    category: FlashCategory = FlashCategory.INFO
    timeout: int | None = 5

    def flash(self, request: Request) -> None:
        """Add this message to the session."""
        if MESSAGES not in request.session:
            request.session[MESSAGES] = []
        request.session[MESSAGES].append(self.model_dump())


class FormErrorMessage(FlashMessage):
    """Message to be displayed to the user for form errors.

    Includes commonsense defaults for form errors.
    Typically this error would not call flash() directly, but instead
    be passed to the TemplateResponse.
    """

    text: str = DEFAULT_FORM_ERROR_MESSAGE
    category: FlashCategory = FlashCategory.ERROR
    timeout: int | None = None


def get_flashed_messages(request: Request) -> list[FlashMessage]:
    """Get flashed messages from the session."""
    messages = cast(list[dict], request.session.pop(MESSAGES, []))
    return [FlashMessage(**msg) for msg in messages]
