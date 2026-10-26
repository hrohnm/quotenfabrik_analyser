"""league flag: core.leagues.flag_url (country flag from API-Football, backfilled from the raw fixtures)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-26 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leagues", sa.Column("flag_url", sa.Text(), nullable=True), schema="core")
    op.execute(
        """
        update core.leagues l set flag_url = x.flag
        from (
            select distinct on ((item->'league'->>'id')::int) (item->'league'->>'id')::int as id,
                   item->'league'->>'flag' as flag
            from raw.api_responses r, jsonb_array_elements(r.payload->'response') item
            where r.endpoint = 'fixtures' and item->'league'->>'flag' is not null
            order by (item->'league'->>'id')::int, r.id desc
        ) x
        where l.id = x.id
        """
    )


def downgrade() -> None:
    op.drop_column("leagues", "flag_url", schema="core")
