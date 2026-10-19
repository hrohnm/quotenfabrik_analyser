"""league kind: full leagues vs. results-only leagues for the strength scale

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-20 08:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "leagues", sa.Column("kind", sa.Text(), server_default="full", nullable=False), schema="app"
    )
    op.execute("ALTER TABLE app.leagues ADD CONSTRAINT ck_leagues_kind CHECK (kind IN ('full', 'ratings'))")


def downgrade() -> None:
    op.execute("ALTER TABLE app.leagues DROP CONSTRAINT ck_leagues_kind")
    op.drop_column("leagues", "kind", schema="app")
