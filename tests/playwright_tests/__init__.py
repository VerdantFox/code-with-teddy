"""__init__: playwright tests package."""

from dataclasses import dataclass

from tests import Environment

ENVIRONMENT_MAP = {
    Environment.LOCAL: "http://localhost:8000",
    Environment.DOCKER: "http://localhost",
    Environment.PROD: "https://not-yet-determined.com",
}


@dataclass
class UIDetails:
    """Class to hold authentication details."""

    url: str
    basic_username: str
    basic_password: str
    admin_username: str
    admin_password: str
