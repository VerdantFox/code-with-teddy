"""web_user_handlers: helper functions for working with web users."""
from fastapi import Response

from app import constants


def set_guest_user_id_cookie(*, guest_id: str, response: Response) -> None:
    """Set the guest user id cookie and context on the response."""
    response.set_cookie(
        constants.GUEST_ID,
        guest_id,
        max_age=constants.ONE_YEAR_IN_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
    )
