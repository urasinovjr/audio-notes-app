"""change_user_id_to_string

Revision ID: 5082b6830963
Revises: 089602b2c740
Create Date: 2025-11-19 14:30:17.042422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5082b6830963'
down_revision: Union[str, Sequence[str], None] = '089602b2c740'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Change user ID from integer to string for Supertokens compatibility.

    Note: This migration will delete all existing data since we cannot
    convert integer IDs to string UUIDs.
    """
    # Drop foreign key constraint first
    op.drop_constraint('audio_notes_user_id_fkey', 'audio_notes', type_='foreignkey')

    # Delete all existing data (cannot migrate int IDs to string UUIDs)
    op.execute('DELETE FROM audio_notes')
    op.execute('DELETE FROM users')

    # Change users.id from INTEGER to VARCHAR(255)
    op.alter_column('users', 'id',
                    existing_type=sa.INTEGER(),
                    type_=sa.String(255),
                    existing_nullable=False,
                    autoincrement=False)

    # Change audio_notes.user_id from INTEGER to VARCHAR(255)
    op.alter_column('audio_notes', 'user_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.String(255),
                    existing_nullable=False)

    # Re-create foreign key constraint
    op.create_foreign_key('audio_notes_user_id_fkey', 'audio_notes', 'users',
                         ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema: Revert user ID from string to integer.

    Note: This will delete all existing data.
    """
    # Drop foreign key constraint first
    op.drop_constraint('audio_notes_user_id_fkey', 'audio_notes', type_='foreignkey')

    # Delete all existing data
    op.execute('DELETE FROM audio_notes')
    op.execute('DELETE FROM users')

    # Change audio_notes.user_id from VARCHAR(255) to INTEGER
    op.alter_column('audio_notes', 'user_id',
                    existing_type=sa.String(255),
                    type_=sa.INTEGER(),
                    existing_nullable=False)

    # Change users.id from VARCHAR(255) to INTEGER
    op.alter_column('users', 'id',
                    existing_type=sa.String(255),
                    type_=sa.INTEGER(),
                    existing_nullable=False,
                    autoincrement=True)

    # Re-create foreign key constraint
    op.create_foreign_key('audio_notes_user_id_fkey', 'audio_notes', 'users',
                         ['user_id'], ['id'], ondelete='CASCADE')
