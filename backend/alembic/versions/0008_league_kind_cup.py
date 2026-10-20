"""league kind 'cup' (European cups: link the leagues of the strength scale)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-20 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE app.leagues DROP CONSTRAINT ck_leagues_kind")
    op.execute(
        "ALTER TABLE app.leagues ADD CONSTRAINT ck_leagues_kind CHECK (kind IN ('full', 'ratings', 'cup'))"
    )


def downgrade() -> None:
    op.execute("DELETE FROM app.leagues WHERE kind = 'cup'")
    op.execute("ALTER TABLE app.leagues DROP CONSTRAINT ck_leagues_kind")
    op.execute("ALTER TABLE app.leagues ADD CONSTRAINT ck_leagues_kind CHECK (kind IN ('full', 'ratings'))")
