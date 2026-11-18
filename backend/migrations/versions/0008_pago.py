"""Pagos de mensualidad con ciclo anclado y anulación.

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pago",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("vehiculo_id", sa.BigInteger(), nullable=False),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.Column("referencia", sa.Text(), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("dia_corte", sa.Integer(), nullable=False),
        sa.Column("inicio_ciclo", sa.Date(), nullable=False),
        sa.Column("vencimiento_ciclo", sa.Date(), nullable=False),
        sa.Column("anulacion_fecha_hora", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulacion_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("anulacion_motivo", sa.Text(), nullable=True),
        sa.CheckConstraint("valor > 0", name="ck_pago_valor_positivo"),
        sa.CheckConstraint("referencia ~ '[^[:space:]]'", name="ck_pago_referencia_no_vacia"),
        sa.CheckConstraint(
            "referencia = regexp_replace(referencia, '^[[:space:]]+|[[:space:]]+$', '', 'g')",
            name="ck_pago_referencia_normalizada",
        ),
        sa.CheckConstraint("dia_corte BETWEEN 1 AND 31", name="ck_pago_dia_corte"),
        sa.CheckConstraint("inicio_ciclo < vencimiento_ciclo", name="ck_pago_ciclo_orden"),
        sa.CheckConstraint(
            "anulacion_motivo IN ('Error de digitación', 'Valor incorrecto', "
            "'Pago duplicado', 'Recibo no válido', 'Otro')",
            name="ck_pago_motivo_anulacion",
        ),
        sa.CheckConstraint(
            "(anulacion_fecha_hora IS NULL) = (anulacion_usuario_id IS NULL) "
            "AND (anulacion_fecha_hora IS NULL) = (anulacion_motivo IS NULL)",
            name="ck_pago_anulacion_completa",
        ),
        sa.ForeignKeyConstraint(
            ["vehiculo_id"], ["vehiculo.id"], name="fk_pago_vehiculo", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name="fk_pago_usuario", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["anulacion_usuario_id"],
            ["usuario.id"],
            name="fk_pago_anulacion_usuario",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_pago_referencia_activa",
        "pago",
        ["referencia"],
        unique=True,
        postgresql_where=sa.text("anulacion_fecha_hora IS NULL"),
    )
    op.create_index("ix_pago_vehiculo_fecha", "pago", ["vehiculo_id", "fecha_hora"])


def downgrade() -> None:
    op.drop_index("ix_pago_vehiculo_fecha", table_name="pago")
    op.drop_index("uq_pago_referencia_activa", table_name="pago")
    op.drop_table("pago")
