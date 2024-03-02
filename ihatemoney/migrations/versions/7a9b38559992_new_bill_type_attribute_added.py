"""new bill type attribute added

Revision ID: 7a9b38559992
Revises: 927ed575acbd
Create Date: 2022-12-10 17:25:38.387643

"""

# revision identifiers, used by Alembic.
revision = "7a9b38559992"
down_revision = "927ed575acbd"

from alembic import op
import sqlalchemy as sa
from ihatemoney.models import BillType


def upgrade():
    op.add_column("bill", sa.Column("bill_type", sa.Enum(BillType)))
    op.add_column("bill_version", sa.Column("bill_type", sa.UnicodeText()))


def downgrade():
    pass
