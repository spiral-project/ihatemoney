"""hash project passwords

Revision ID: b78f8a8bdb16
Revises: f629c8ef4ab0
Create Date: 2017-12-17 11:45:44.783238

"""

# revision identifiers, used by Alembic.
revision = "b78f8a8bdb16"
down_revision = "f629c8ef4ab0"

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

project_helper = sa.Table(
    "project",
    sa.MetaData(),
    sa.Column("id", sa.String(length=64), nullable=False),
    sa.Column("name", sa.UnicodeText(), nullable=True),
    sa.Column("password", sa.String(length=128), nullable=True),
    sa.Column("contact_email", sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint("id"),
)


def upgrade():
    connection = op.get_bind()
    for project in connection.execute(project_helper.select()):
        connection.execute(
            project_helper.update()
            .where(project_helper.c.name == project.name)
            .values(password=generate_password_hash(project.password))
        )


def downgrade():
    # Downgrade path is not possible, because information has been lost.
    pass
