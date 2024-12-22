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

import asyncio
import os
import random
import textwrap
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import faker
import typer
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import permissions
from app.datastore import db_models
from app.datastore.database import get_engine
from app.services.blog import blog_handler, blog_utils
from app.services.general import auth_helpers

# DB connection constants
DB_STRING_KEY = "DB_CONNECTION_STRING"
EXAMPLE_BP_DIR = Path(__file__).parent.parent / "tests" / "data" / "example_blog_posts"

# datetime constants
TIMEZONE = UTC
TODAY = datetime.now(tz=TIMEZONE)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
THREE_DAYS_PAST = TODAY - timedelta(days=3)
THREE_DAYS_FUTURE = TODAY + timedelta(days=3)
LAST_MONTH = TODAY - timedelta(days=30)
LAST_WEEK = TODAY - timedelta(days=7)
NEXT_WEEK = TODAY + timedelta(days=7)

FAKER = faker.Faker()


async def populate_database(connection_string: str | None = None) -> None:
    """Run the populate db script."""
    db_connection_before = os.environ.get(DB_STRING_KEY)
    if connection_string:
        os.environ[DB_STRING_KEY] = connection_string

    engine = get_engine(connection_string=connection_string)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        pop_db = PopulateDB(session=session)
        await pop_db.populate()

    if db_connection_before:
        os.environ[DB_STRING_KEY] = db_connection_before


class PopulateDB:
    """Populates the database with dummy data."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the class."""
        self.session = session
        self.users: list[db_models.User] = []
        self.blog_posts: list[db_models.BlogPost] = []

    async def populate(self) -> None:
        """Populate the database with dummy data."""
        await self.populate_users()
        await self.populate_blog_posts()
        await self.populate_bp_series()

    async def populate_users(self) -> None:
        """Populate the users table."""
        self.users = [
            db_models.User(
                username="rand",
                email="dragon@gmail.com",
                full_name="Rand Al'Thor",
                timezone="America/Denver",
                password_hash=auth_helpers.hash_password("password"),
                role=permissions.Role.ADMIN,
                avatar_location="/media/local/rand.jpeg",
            ),
            db_models.User(
                username="mat",
                email="alwayslucky@email.com",
                full_name="Matrim Cauthon",
                timezone="America/Chicago",
                password_hash=auth_helpers.hash_password("password"),
                role=permissions.Role.USER,
                avatar_location="https://static.wikia.nocookie.net/wot/images/c/cb/Mat_cauthon_son_of_battles_by_reddera-d993o0f.jpg",
            ),
            db_models.User(
                username="perrin",
                email="wolfboy@email.com",
                full_name="Perrin Aybara",
                timezone="America/Seattle",
                password_hash=auth_helpers.hash_password("password"),
                role=permissions.Role.USER,
            ),
            db_models.User(
                username="egwene",
                email="magicmaiden@email.com",
                full_name="Egwene al'Vere",
                timezone="America/Denver",
                password_hash=auth_helpers.hash_password("password"),
                role=permissions.Role.REVIEWER,
                avatar_location="https://static.wikia.nocookie.net/wot-prime/images/e/e1/Egwene_s2_icon.jpg",
            ),
        ]
        for user in self.users:
            self.session.add(user)
        await self.session.commit()
        for user in self.users:
            await self.session.refresh(user)

    async def populate_blog_posts(self) -> None:
        """Populate the blog_posts table."""
        self.blog_posts = [
            await self.populate_blog_post_from_path(bp_path) for bp_path in EXAMPLE_BP_DIR.iterdir()
        ]

    async def populate_blog_post_from_path(self, blog_post_path: Path) -> db_models.BlogPost:
        """Populate a blog post and peripheral data from a Path."""
        bp = await self.create_bp_from_path(blog_post_path)
        await self.populate_bp_peripherals(bp)
        return bp

    async def create_bp_from_path(self, blog_post_path: Path) -> db_models.BlogPost:
        """Generate a blog post from a Path."""
        file_content = blog_post_path.read_text()
        title = blog_utils.get_bp_title(file_content)
        md_content = blog_utils.get_bp_content(file_content)
        md_description = blog_utils.get_bp_introduction(file_content)
        tags = blog_utils.get_bp_tags(file_content)
        thumbnail_url = blog_utils.get_bp_thumbnail(file_content)
        data = blog_handler.SaveBlogInput(
            title=title,
            tags=tags,
            is_published=True,
            can_comment=True,
            description=md_description,
            content=md_content,
            thumbnail_url=thumbnail_url,
        )
        response = await blog_handler.save_blog_post(db=self.session, data=data)
        if not response.blog_post:
            err_msg = f"Failed to save blog post: {response.err_msg}"
            raise ValueError(err_msg)
        return response.blog_post

    async def populate_bp_peripherals(self, blog_post: db_models.BlogPost) -> None:
        """Populate the blog post with peripheral data."""
        blog_post.likes = random.randint(0, 100)
        blog_post.views = random.randint(0, 10_000)
        blog_post.created_timestamp = LAST_MONTH + timedelta(
            days=random.randint(1, 15), hours=random.randint(1, 23)
        )
        blog_post.updated_timestamp = blog_post.created_timestamp + timedelta(
            days=random.randint(0, 10), hours=random.randint(0, 23)
        )
        await self.session.commit()
        await self.session.refresh(blog_post)
        for _ in range(random.randint(1, 5)):
            await self.create_comment(blog_post)

    async def create_comment(self, blog_post: db_models.BlogPost) -> None:
        """Create a comment for a blog post."""
        is_guest = random.choice([True, False])
        content = textwrap.dedent(
            f"""\
            {FAKER.paragraph()}

            ## {FAKER.sentence()}

            {FAKER.paragraph()}
            """
        )
        data = blog_handler.SaveCommentInput(
            bp_id=blog_post.id,
            guest_id=f"guest_id_{random.randint(1, 1000)}" if is_guest else None,
            name="Guest Name" if is_guest else None,
            email="guest@email.com" if is_guest else None,
            user_id=None if is_guest else random.choice(self.users).id,
            content=content,
        )
        await blog_handler.save_new_comment(db=self.session, data=data)

    async def populate_bp_series(self) -> None:
        """Populate the blog post series table."""
        series = await blog_handler.create_series(
            db=self.session,
            name="The Wheel of Time",
            description="A series of blog posts about The Wheel of Time.",
        )
        for blog_post in self.blog_posts[:2]:
            blog_post.series_id = series.id
        await self.session.commit()


cli_app = typer.Typer(add_completion=False, no_args_is_help=True, pretty_exceptions_enable=False)


@cli_app.command()
def typer_main(
    *,
    connection_string: Annotated[
        str, typer.Option(help="database connection string.")
    ] = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
) -> None:
    """Create a postgres docker container and postgres database with tables."""
    try:
        asyncio.run(populate_database(connection_string=connection_string))
    except OperationalError as e:
        typer.echo(f"Error: {e}")
        typer.echo("Failed to connect to the postgres instance.")
        typer.echo(
            "You can start the local postgres instance with `./dev_tools/start-local-postgres.sh`."
        )
        typer.echo(
            "For docker deployed app, set the --connection-string to the postgres"
            " connection string (in ./secrets/db_connection_string) replacing db -> localhost."
        )
        raise typer.Exit(1) from e


if __name__ == "__main__":
    cli_app()
