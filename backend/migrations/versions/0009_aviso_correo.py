"""Avisos por correo, datos de contacto y vencimiento derivado.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehiculo", sa.Column("correo", sa.Text(), nullable=True))
    op.add_column(
        "vehiculo",
        sa.Column(
            "avisos_autorizados",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "vehiculo", sa.Column("autorizacion_usuario_id", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "vehiculo", sa.Column("autorizacion_fecha_hora", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_vehiculo_autorizacion_usuario",
        "vehiculo",
        "usuario",
        ["autorizacion_usuario_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_vehiculo_correo_normalizado",
        "vehiculo",
        "correo IS NULL OR correo = regexp_replace(correo, '^[[:space:]]+|[[:space:]]+$', '', 'g')",
    )
    op.create_check_constraint(
        "ck_vehiculo_autorizacion_completa",
        "vehiculo",
        "avisos_autorizados = (autorizacion_usuario_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_vehiculo_autorizacion_fecha",
        "vehiculo",
        "(autorizacion_usuario_id IS NULL) = (autorizacion_fecha_hora IS NULL)",
    )

    op.create_table(
        "aviso",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("vehiculo_id", sa.BigInteger(), nullable=False),
        sa.Column("correo", sa.Text(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("resultado IN ('ENVIADO', 'FALLIDO')", name="ck_aviso_resultado"),
        sa.CheckConstraint("correo ~ '[^[:space:]]'", name="ck_aviso_correo_no_vacio"),
        sa.ForeignKeyConstraint(
            ["vehiculo_id"], ["vehiculo.id"], name="fk_aviso_vehiculo", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_aviso_enviado",
        "aviso",
        ["vehiculo_id", "fecha_vencimiento"],
        unique=True,
        postgresql_where=sa.text("resultado = 'ENVIADO'"),
    )
    op.create_index("ix_aviso_fecha_hora", "aviso", ["fecha_hora"])

    # El vencimiento deja de escribirse a mano: se deriva de pago (RN-VIG-01).
    op.drop_column("vehiculo", "fecha_vencimiento")


def downgrade() -> None:
    op.add_column("vehiculo", sa.Column("fecha_vencimiento", sa.Date(), nullable=True))
    op.execute(
        "UPDATE vehiculo AS v SET fecha_vencimiento = COALESCE("
        "(SELECT MAX(p.vencimiento_ciclo) FROM pago AS p "
        "WHERE p.vehiculo_id = v.id AND p.anulacion_fecha_hora IS NULL), CURRENT_DATE)"
    )
    op.alter_column(
        "vehiculo", "fecha_vencimiento", existing_type=sa.Date(), nullable=False
    )

    op.drop_index("ix_aviso_fecha_hora", table_name="aviso")
    op.drop_index("uq_aviso_enviado", table_name="aviso")
    op.drop_table("aviso")

    op.drop_constraint("ck_vehiculo_autorizacion_fecha", "vehiculo", type_="check")
    op.drop_constraint("ck_vehiculo_autorizacion_completa", "vehiculo", type_="check")
    op.drop_constraint("ck_vehiculo_correo_normalizado", "vehiculo", type_="check")
    op.drop_constraint("fk_vehiculo_autorizacion_usuario", "vehiculo", type_="foreignkey")
    op.drop_column("vehiculo", "autorizacion_fecha_hora")
    op.drop_column("vehiculo", "autorizacion_usuario_id")
    op.drop_column("vehiculo", "avisos_autorizados")
    op.drop_column("vehiculo", "correo")
