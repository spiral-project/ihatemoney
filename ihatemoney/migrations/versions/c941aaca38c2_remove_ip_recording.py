"""remove ip recording

Revision ID: c941aaca38c2
Revises: 06884b17c50f
Create Date: 2026-05-09 11:05:35.485838

"""

# revision identifiers, used by Alembic.
revision = 'c941aaca38c2'
down_revision = '06884b17c50f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=sa.VARCHAR(length=128),
               type_=sa.String(length=256),
               existing_nullable=True)
        batch_op.alter_column('logging_preference',
               existing_type=sa.VARCHAR(length=9),
               type_=sa.Enum('DISABLED', 'ENABLED', name='loggingmode'),
               existing_nullable=False,
               existing_server_default=sa.text("'ENABLED'"))

    with op.batch_alter_table('project_version', schema=None) as batch_op:
        batch_op.alter_column('logging_preference',
               existing_type=sa.VARCHAR(length=9),
               existing_nullable=True,
               autoincrement=False,
               existing_server_default=sa.text("'ENABLED'"))

    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.drop_column('remote_addr')

    # data migration
    op.execute(
        """
        UPDATE project
        SET logging_preference = 'ENABLED'
        WHERE logging_preference = 'RECORD_IP'
        """
    )



def downgrade():
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.add_column(sa.Column('remote_addr', sa.VARCHAR(length=50), nullable=True))

    with op.batch_alter_table('project_version', schema=None) as batch_op:
        batch_op.alter_column('logging_preference',
               existing_type=sa.Enum('DISABLED', 'ENABLED', name='loggingmode'),
               type_=sa.VARCHAR(length=9),
               existing_nullable=True,
               autoincrement=False,
               existing_server_default=sa.text("'ENABLED'"))

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column('logging_preference',
               existing_type=sa.Enum('DISABLED', 'ENABLED', name='loggingmode'),
               type_=sa.VARCHAR(length=9),
               existing_nullable=False,
               existing_server_default=sa.text("'ENABLED'"))
    # no rollback for data migration
