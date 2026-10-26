"""chosen run index: partial index on the 1X2 home prediction per fixture and run (``CHOSEN_RUNS_SQL``)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-26 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        create index if not exists ix_predictions_chosen_run on analytics.predictions
            (fixture_id, model_run_id) include (predicted_at)
            where market = '1x2' and selection = 'H'
        """
    )


def downgrade() -> None:
    op.execute("drop index if exists analytics.ix_predictions_chosen_run")
