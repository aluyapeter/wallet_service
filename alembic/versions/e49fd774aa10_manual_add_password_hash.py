"""manual_add_password_hash

Revision ID: [KEEP_THE_GENERATED_ID_HERE]
Revises: 10f4088a6ca5
Create Date: 2026-01-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
# DO NOT CHANGE THE 'revision' VARIABLE THAT WAS ALREADY HERE
revision: str = 'e49fd774aa10'
down_revision: Union[str, Sequence[str], None] = '10f4088a6ca5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password_hash (nullable is True)
    op.add_column('user', sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # Add is_email_verified (default false, nullable false)
    # We use server_default='false' to fill existing rows with False
    op.add_column('user', sa.Column('is_email_verified', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('user', 'is_email_verified')
    op.drop_column('user', 'password_hash')