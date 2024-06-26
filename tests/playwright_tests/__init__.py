"""__init__: playwright tests package."""

from dataclasses import dataclass

from app.settings import Environment

ENVIRONMENT_MAP = {
    Environment.LOCAL: "http://localhost:8000",
    Environment.DOCKER: "http://localhost",
    Environment.PROD: "https://codewithteddy.dev",
}


@dataclass
class UIDetails:
    """Class to hold authentication details."""

    environment: Environment
    url: str
    basic_username: str
    basic_password: str
    admin_username: str
    admin_password: str
