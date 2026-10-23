"""Teléfono del operador opcional.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TELEFONO_AL_REVERTIR = "SIN DATO"


def upgrade() -> None:
    # Decisión 9: el teléfono del operador es opcional.
    op.alter_column("operador", "telefono", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # ck_operador_telefono_no_vacio acepta NULL (un CHECK con NULL no falla),
    # así que hay que rellenar los valores antes de volver a NOT NULL.
    op.execute(
        sa.text(
            "UPDATE operador SET telefono = :valor WHERE telefono IS NULL"
        ).bindparams(valor=TELEFONO_AL_REVERTIR)
    )
    op.alter_column("operador", "telefono", existing_type=sa.Text(), nullable=False)
