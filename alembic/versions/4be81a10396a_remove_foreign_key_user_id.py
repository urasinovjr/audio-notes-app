"""remove_foreign_key_user_id

Revision ID: 4be81a10396a
Revises: 5082b6830963
Create Date: 2025-11-19 15:03:15.014331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4be81a10396a'
down_revision: Union[str, Sequence[str], None] = '5082b6830963'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('audio_notes_user_id_fkey', 'audio_notes', type_='foreignkey')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_foreign_key(
        'audio_notes_user_id_fkey',
        'audio_notes', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
