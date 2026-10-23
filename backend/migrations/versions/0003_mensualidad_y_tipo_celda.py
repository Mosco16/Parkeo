"""Agrega fecha de vencimiento y restringe el tipo de celda.

Revision ID: 0003
Revises: 0002
"""

from alembic import context, op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Una mensualidad nueva vence en un mes; se usa solo para los vehículos que
# ya existían cuando se aplica esta migración.
DIAS_VIGENCIA_POR_DEFECTO = 30


def upgrade() -> None:
    # RN-VIG-01: cada vehículo tiene una fecha de vencimiento, sin hora.
    op.add_column("vehiculo", sa.Column("fecha_vencimiento", sa.Date(), nullable=True))
    op.execute(
        "UPDATE vehiculo "
        f"SET fecha_vencimiento = CURRENT_DATE + {DIAS_VIGENCIA_POR_DEFECTO} "
        "WHERE fecha_vencimiento IS NULL"
    )
    op.alter_column("vehiculo", "fecha_vencimiento", existing_type=sa.Date(), nullable=False)

    # RN-CEL-02: una celda es de un solo tipo. Convertir primero los datos.
    op.execute("UPDATE celda SET tipo = 'AUTO' WHERE upper(codigo) LIKE 'A%'")
    op.execute("UPDATE celda SET tipo = 'MOTO' WHERE upper(codigo) LIKE 'M%'")
    if not context.is_offline_mode():
        pendientes = op.get_bind().execute(
            sa.text("SELECT count(*) FROM celda WHERE tipo NOT IN ('AUTO', 'MOTO')")
        ).scalar_one()
        if pendientes:
            raise RuntimeError(
                f"Hay {pendientes} celdas cuyo tipo no es AUTO ni MOTO y cuyo código "
                "no empieza por A ni por M. Corrige esas filas antes de aplicar la "
                "migración."
            )
    op.create_check_constraint("ck_celda_tipo", "celda", "tipo IN ('AUTO', 'MOTO')")


def downgrade() -> None:
    op.drop_constraint("ck_celda_tipo", "celda", type_="check")
    op.drop_column("vehiculo", "fecha_vencimiento")
