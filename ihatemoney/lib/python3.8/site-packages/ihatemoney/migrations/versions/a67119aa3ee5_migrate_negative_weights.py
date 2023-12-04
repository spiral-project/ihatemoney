"""Migrate negative weights

Revision ID: a67119aa3ee5
Revises: afbf27e6ef20
Create Date: 2018-12-25 18:34:20.220844

"""

# revision identifiers, used by Alembic.
revision = "a67119aa3ee5"
down_revision = "afbf27e6ef20"

from alembic import op
import sqlalchemy as sa

# Snapshot of the person table
person_helper = sa.Table(
    "person",
    sa.MetaData(),
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("project_id", sa.String(length=64), nullable=True),
    sa.Column("name", sa.UnicodeText(), nullable=True),
    sa.Column("activated", sa.Boolean(), nullable=True),
    sa.Column("weight", sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
    sa.PrimaryKeyConstraint("id"),
)


def upgrade():
    op.execute(
        person_helper.update().where(person_helper.c.weight <= 0).values(weight=1)
    )


def downgrade():
    # Downgrade path is not possible, because information has been lost.
    pass
