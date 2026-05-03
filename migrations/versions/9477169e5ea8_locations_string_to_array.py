"""Locations string to array.

Revision ID: 9477169e5ea8
Revises: 45dfd4469e80
Create Date: 2026-05-03 15:02:49.872960

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9477169e5ea8"
down_revision: str | None = "45dfd4469e80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "blog_post_media",
        sa.Column("locations_array", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.execute("UPDATE blog_post_media SET locations_array = string_to_array(locations, ',')")
    op.drop_column("blog_post_media", "locations")
    op.alter_column(
        "blog_post_media", "locations_array", new_column_name="locations", nullable=False
    )


def downgrade() -> None:
    op.add_column(
        "blog_post_media",
        sa.Column("locations_str", sa.String(), nullable=True),
    )
    op.execute("UPDATE blog_post_media SET locations_str = array_to_string(locations, ',')")
    op.drop_column("blog_post_media", "locations")
    op.alter_column("blog_post_media", "locations_str", new_column_name="locations", nullable=False)
