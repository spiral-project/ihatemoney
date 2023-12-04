"""sqlite_autoincrement

Revision ID: cb038f79982e
Revises: 2dcb0c0048dc
Create Date: 2020-04-13 17:40:02.426957

"""

# revision identifiers, used by Alembic.
revision = "cb038f79982e"
down_revision = "2dcb0c0048dc"

from alembic import op
import sqlalchemy as sa


def upgrade():
    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        alter_table_batches = [
            op.batch_alter_table(
                "person", recreate="always", table_kwargs={"sqlite_autoincrement": True}
            ),
            op.batch_alter_table(
                "bill", recreate="always", table_kwargs={"sqlite_autoincrement": True}
            ),
            op.batch_alter_table(
                "billowers",
                recreate="always",
                table_kwargs={"sqlite_autoincrement": True},
            ),
        ]

        for batch_op in alter_table_batches:
            with batch_op:
                pass


def downgrade():
    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        alter_table_batches = [
            op.batch_alter_table(
                "person",
                recreate="always",
                table_kwargs={"sqlite_autoincrement": False},
            ),
            op.batch_alter_table(
                "bill", recreate="always", table_kwargs={"sqlite_autoincrement": False}
            ),
            op.batch_alter_table(
                "billowers",
                recreate="always",
                table_kwargs={"sqlite_autoincrement": False},
            ),
        ]

        for batch_op in alter_table_batches:
            with batch_op:
                pass
