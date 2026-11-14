"""add campaign offer states

Revision ID: 568bd7ab16ea
Revises:
Create Date: 2026-11-14 05:56:08.625047

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "568bd7ab16ea"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # New empty table: inline uniqueness needs no concurrent index build.
    op.create_table(
        "campaign_offer_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("stream_name", sa.String(length=255), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("offer_name", sa.String(length=255), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "stream_id", "offer_id", name="uq_campaign_stream_offer"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("campaign_offer_states")
