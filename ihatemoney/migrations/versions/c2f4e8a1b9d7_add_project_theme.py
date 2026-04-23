"""add project.theme field

Revision ID: c2f4e8a1b9d7
Revises: 06884b17c50f
Create Date: 2026-04-23 00:00:00.000000

"""

revision = "c2f4e8a1b9d7"
down_revision = "06884b17c50f"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        "project",
        sa.Column("theme", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "project_version",
        sa.Column(
            "theme", sa.String(length=16), autoincrement=False, nullable=True
        ),
    )


def downgrade():
    op.drop_column("project_version", "theme")
    op.drop_column("project", "theme")
