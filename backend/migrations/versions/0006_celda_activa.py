"""Celda activa para mantenimiento.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Las celdas existentes quedan activas; el administrador las apaga una a una.
    op.add_column(
        "celda",
        sa.Column(
            "activa", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )


def downgrade() -> None:
    op.drop_column("celda", "activa")
