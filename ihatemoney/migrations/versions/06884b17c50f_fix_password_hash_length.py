"""fix password hash length

Revision ID: 06884b17c50f
Revises: 7a9b38559992
Create Date: 2026-02-03 21:41:18.628173

"""

# revision identifiers, used by Alembic.
revision = '06884b17c50f'
down_revision = '7a9b38559992'

from alembic import op
import sqlalchemy as sa
from ihatemoney.migrations import utils

@utils.skip_if_sqlite
def upgrade():
    op.alter_column("project","password", type_=sa.String(length=256))
    op.alter_column("project_version","password", type_=sa.String(length=256))

@utils.skip_if_sqlite
def downgrade():
    op.alter_column("project","password", type_=sa.String(length=128))
    op.alter_column("project_version","password", type_=sa.String(length=128))
