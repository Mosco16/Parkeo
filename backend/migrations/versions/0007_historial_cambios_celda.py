"""Historial append-only de los cambios de celda.

Revision ID: 0007
Revises: 0006
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cambio_celda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("estancia_id", sa.BigInteger(), nullable=False),
        sa.Column("celda_anterior_id", sa.BigInteger(), nullable=False),
        sa.Column("celda_nueva_id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "celda_anterior_id <> celda_nueva_id",
            name="ck_cambio_celda_celdas_distintas",
        ),
        sa.ForeignKeyConstraint(
            ["estancia_id"],
            ["estancia.id"],
            name="fk_cambio_celda_estancia",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["celda_anterior_id"],
            ["celda.id"],
            name="fk_cambio_celda_celda_anterior",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["celda_nueva_id"],
            ["celda.id"],
            name="fk_cambio_celda_celda_nueva",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_cambio_celda_usuario",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cambio_celda_fecha_hora", "cambio_celda", ["fecha_hora"])


def downgrade() -> None:
    op.drop_index("ix_cambio_celda_fecha_hora", table_name="cambio_celda")
    op.drop_table("cambio_celda")
