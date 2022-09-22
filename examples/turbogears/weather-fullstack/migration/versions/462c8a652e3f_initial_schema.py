"""Initial Schema

Revision ID: 462c8a652e3f
Revises: None
Create Date: 2022-09-22 20:49:04.054205

"""

# revision identifiers, used by Alembic.
revision = '462c8a652e3f'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'tg_user',
        sa.Column('user_id', sa.Integer, primary_key=True),
        sa.Column('user_name', sa.String(16), nullable=False),
        sa.Column('email_address', sa.Unicode(255)),
        sa.Column('display_name', sa.Unicode(255)),
        sa.Column('password', sa.Unicode(128)),
        sa.Column('created', sa.Date()),
    )


def downgrade():
    pass
