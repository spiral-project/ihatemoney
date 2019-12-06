"""add project.default_currency field

Revision ID: 5cdb4f2e52c9
Revises: e782dd493cdc
Create Date: 2019-12-06 15:46:03.416256

"""

# revision identifiers, used by Alembic.
revision = '5cdb4f2e52c9'
down_revision = 'e782dd493cdc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("project", sa.Column("default_currency", sa.String(length=3), nullable=True))


def downgrade():
    op.drop_column("project", "default_currency")
