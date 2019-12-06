"""add bill.original_currency and bill.original_amount fields

Revision ID: e782dd493cdc
Revises: 6c6fb2b7f229
Create Date: 2019-12-06 15:12:46.116711

"""

# revision identifiers, used by Alembic.
revision = 'e782dd493cdc'
down_revision = '6c6fb2b7f229'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("bill", sa.Column("original_currency", sa.String(length=3), nullable=True))
    op.add_column("bill", sa.Column("original_amount", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("bill", "original_currency")
    op.drop_column("bill", "original_amount")
