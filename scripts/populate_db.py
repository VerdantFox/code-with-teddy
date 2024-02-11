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
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import permissions
from app.datastore import db_models
from app.datastore.database import Session, engine
from app.services.blog import blog_handler, blog_utils
from app.web import auth

# DB connection constants
DB_STRING_KEY = "DB_CONNECTION_STRING"
LOCAL_DB_CONNECTION_STRING = "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"
EXAMPLE_BP_DIR = Path(__file__).parent.parent / "tests" / "data" / "example_blog_posts"

# datetime constants
TIMEZONE = timezone.utc
TODAY = datetime.now(tz=TIMEZONE)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
THREE_DAYS_PAST = TODAY - timedelta(days=3)
THREE_DAYS_FUTURE = TODAY + timedelta(days=3)
LAST_MONTH = TODAY - timedelta(days=30)
LAST_WEEK = TODAY - timedelta(days=7)
NEXT_WEEK = TODAY + timedelta(days=7)


def populate_database() -> None:
    """Run the populate db script."""
    db_connection_before = os.environ.get(DB_STRING_KEY)
    os.environ[DB_STRING_KEY] = LOCAL_DB_CONNECTION_STRING
    session = Session(engine)
    pop_db = PopulateDB(session=session)
    with session:
        pop_db.populate()

    if db_connection_before:
        os.environ[DB_STRING_KEY] = db_connection_before


class PopulateDB:
    """Populates the database with dummy data."""

    def __init__(self, session: Session) -> None:
        """Initialize the class."""
        self.session = session
        self.users: list[db_models.User] = []
        self.blog_posts: list[db_models.BlogPost] = []

    def _populate_users(self) -> None:
        """Populate the users table."""
        self.users = [
            db_models.User(
                username="rand",
                email="dragon@gmail.com",
                full_name="Rand Al'Thor",
                timezone="America/Denver",
                password_hash=auth.hash_password("password"),
                role=permissions.Role.ADMIN,
                avatar_location="/media/local/rand.jpeg",
            ),
            db_models.User(
                username="mat",
                email="alwayslucky@email.com",
                full_name="Matrim Cauthon",
                timezone="America/Chicago",
                password_hash=auth.hash_password("password"),
                role=permissions.Role.USER,
                avatar_location="https://static.wikia.nocookie.net/wot/images/c/cb/Mat_cauthon_son_of_battles_by_reddera-d993o0f.jpg",
            ),
            db_models.User(
                username="perrin",
                email="wolfboy@email.com",
                full_name="Perrin Aybara",
                timezone="America/Seattle",
                password_hash=auth.hash_password("password"),
                role=permissions.Role.USER,
            ),
            db_models.User(
                username="egwene",
                email="magicmaiden@email.com",
                full_name="Egwene al'Vere",
                timezone="America/Denver",
                password_hash=auth.hash_password("password"),
                role=permissions.Role.REVIEWER,
                avatar_location="https://static.wikia.nocookie.net/wot-prime/images/e/e1/Egwene_s2_icon.jpg",
            ),
        ]
        for user in self.users:
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

    def _populate_blog_posts(self) -> None:
        """Populate the blog_posts table."""
        self.blog_posts = [self.bp_from_path(bp_path) for bp_path in EXAMPLE_BP_DIR.iterdir()]
        # for blog_post in self.blog_posts:
        #     self.session.add(blog_post)
        #     self.session.commit()
        #     self.session.refresh(blog_post)

    def populate(self) -> None:
        """Populate the database with dummy data."""
        self._populate_users()
        self._populate_blog_posts()

    def bp_from_path(self, blog_post_path: Path) -> db_models.BlogPost:
        """Generate a blog post from a Path."""
        file_content = blog_post_path.read_text()
        title = blog_utils.get_bp_title(file_content)
        md_content = blog_utils.get_bp_content(file_content)
        md_description = blog_utils.get_bp_introduction(file_content)
        tags = blog_utils.get_bp_tags(file_content)
        data = blog_handler.SaveBlogInput(
            title=title,
            tags=tags,
            is_published=True,
            can_comment=True,
            description=md_description,
            content=md_content,
        )
        response = blog_handler.save_blog_post(db=self.session, data=data)
        if not response.blog_post:
            err_msg = f"Failed to save blog post: {response.err_msg}"
            raise ValueError(err_msg)
        blog_post = response.blog_post
        # blog_post.comments = self._populate_comments(blog_post)
        blog_post.likes = random.randint(0, 100)
        blog_post.views = random.randint(0, 10_000)
        self.session.commit()
        self.session.refresh(blog_post)
        return blog_post


# def bp_from_path(blog_post_path: Path) -> db_models.BlogPost:
#     """Generate a blog post from a Path."""
#     file_content = blog_post_path.read_text()
#     title = blog_utils.get_bp_title(file_content)
#     slug = blog_utils.get_slug(title)
#     publish_date = LAST_MONTH + timedelta(days=random.randint(1, 15), hours=random.randint(1, 23))
#     last_modified_date = publish_date + timedelta(
#         days=random.randint(0, 10), hours=random.randint(0, 23)
#     )
#     content = blog_utils.get_bp_content(file_content)
#     html_content = markdown_parser.markdown_to_html(file_content)
#     description = blog_utils.get_bp_introduction(file_content)
#     html_description = markdown_parser.markdown_to_html(description)
#     tags = blog_utils.get_bp_tags(file_content)
#     breakpoint()
#     return db_models.BlogPost(
#         title=title,
#         slug=slug,
#         tags=tags,
#         is_published=True,
#         can_comment=True,
#         read_mins=blog_utils.calc_read_mins(content),
#         markdown_description=description,
#         markdown_content=content,
#         html_description=html_description.content,
#         html_content=html_content.content,
#         html_toc=html_content.toc,
#         created_timestamp=publish_date,
#         updated_timestamp=last_modified_date,
#         likes=random.randint(0, 100),
#         views=random.randint(0, 100),
#     )


if __name__ == "__main__":
    populate_database()
