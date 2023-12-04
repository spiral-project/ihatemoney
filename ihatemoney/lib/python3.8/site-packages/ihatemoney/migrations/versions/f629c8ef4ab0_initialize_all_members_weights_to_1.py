"""Initialize all members weights to 1

Revision ID: f629c8ef4ab0
Revises: 26d6a218c329
Create Date: 2016-06-15 09:40:30.400862

"""

# revision identifiers, used by Alembic.
revision = "f629c8ef4ab0"
down_revision = "26d6a218c329"

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
        person_helper.update().where(person_helper.c.weight == None).values(weight=1)
    )


def downgrade():
    # Downgrade path is not possible, because information has been lost.
    pass
