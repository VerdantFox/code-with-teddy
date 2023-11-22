"""Populates the database with some dummy data.

Run with command: `python -m dev_tools.populate_db`

This script should only be run against a local postgres instance.
It sets the `DB_CONNECTION_STRING_SECRET` environment variable to the
local postgres connection string to ensure this.

First, start the local postgres instance with `./dev_tools/start-local-postgres.sh`.
You can run (or not run) this script automatically as the last step of the
`./dev_tools/start-local-postgres.sh` script by supplying the
`--populate/--no-populate` flag to that script. `--populate` is the default.
"""
import os
from datetime import datetime, timedelta, timezone

from app.datastore import db_models
from app.datastore.database import Session

# DB connection constants
DB_STRING_KEY = "DB_CONNECTION_STRING_SECRET"
LOCAL_DB_CONNECTION_STRING = "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"

# datetime constants
TIMEZONE = timezone.utc
TODAY = datetime.now(tz=TIMEZONE)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
THREE_DAYS_PAST = TODAY - timedelta(days=3)
THREE_DAYS_FUTURE = TODAY + timedelta(days=3)
LAST_WEEK = TODAY - timedelta(days=7)
NEXT_WEEK = TODAY + timedelta(days=7)


class PopulateDB:
    """Populates the database with dummy data."""

    def __init__(self, session: Session) -> None:
        """Initialize the class."""
        self.session = session
        self.users: list[db_models.User] = []

    def _populate_users(self) -> None:
        """Populate the users table."""
        self.users = []

    def populate(self) -> None:
        """Populate the database with dummy data."""
        self._populate_users()


def populate_database(db: Session) -> None:
    """Run the populate db script."""
    db_connection_before = os.environ.get(DB_STRING_KEY)
    os.environ[DB_STRING_KEY] = LOCAL_DB_CONNECTION_STRING
    pop_db = PopulateDB(session=db)
    pop_db.populate()
    if db_connection_before:
        os.environ[DB_STRING_KEY] = db_connection_before


if __name__ == "__main__":
    db = Session()
    populate_database(db)
