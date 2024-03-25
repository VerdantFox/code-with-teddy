"""responses: Potential responses for the API."""

from fastapi import status

UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        "content": {
            "application/json": {
                "example": {"detail": "Incorrect username or password"},
            },
        },
    },
}
