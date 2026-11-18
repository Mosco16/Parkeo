"""Convierte operador en usuario con credenciales, rol y datos de cuenta.

Revision ID: 0005
Revises: 0004

Las cuentas existentes reciben una contraseña temporal idéntica a la de
demostración (``Parkeo2026*``) y el rol OPERADOR. El script de datos de
demostración siembra además la cuenta administradora.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Hash bcrypt (costo 12) de la contraseña temporal "Parkeo2026*".
# Solo se usa para que las cuentas migradas puedan iniciar sesión una vez y
# cambiarla; no otorga ningún privilegio administrativo.
PASSWORD_TEMPORAL = "$2b$12$x/pxVMzR2xesb0vERJcYVuOjT75NDf5JyIiKurS2mYxJAhUIU6a6C"


def upgrade() -> None:
    op.rename_table("operador", "usuario")
    op.execute("ALTER TABLE usuario RENAME CONSTRAINT operador_pkey TO usuario_pkey")
    op.execute(
        "ALTER TABLE usuario RENAME CONSTRAINT ck_operador_nombre_no_vacio TO ck_usuario_nombre_no_vacio"
    )
    op.execute(
        "ALTER TABLE usuario RENAME CONSTRAINT ck_operador_telefono_no_vacio TO ck_usuario_telefono_no_vacio"
    )

    op.alter_column(
        "estancia",
        "operador_entrada_id",
        new_column_name="usuario_entrada_id",
        existing_type=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "estancia",
        "operador_salida_id",
        new_column_name="usuario_salida_id",
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )
    op.execute(
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_operador_entrada TO fk_estancia_usuario_entrada"
    )
    op.execute(
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_operador_salida TO fk_estancia_usuario_salida"
    )

    op.add_column("usuario", sa.Column("documento", sa.Text(), nullable=True))
    op.add_column("usuario", sa.Column("usuario", sa.Text(), nullable=True))
    op.add_column("usuario", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column("usuario", sa.Column("rol", sa.Text(), nullable=True))
    op.add_column(
        "usuario",
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("usuario", sa.Column("correo", sa.Text(), nullable=True))
    op.add_column("usuario", sa.Column("direccion", sa.Text(), nullable=True))
    op.add_column(
        "usuario",
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "usuario",
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.execute(
        "UPDATE usuario SET "
        "documento = 'DOC' || id, "
        "usuario = 'op' || id, "
        f"password_hash = '{PASSWORD_TEMPORAL}', "
        "rol = 'OPERADOR', "
        "activo = true "
        "WHERE documento IS NULL"
    )

    for column in ("documento", "usuario", "password_hash", "rol"):
        op.alter_column("usuario", column, existing_type=sa.Text(), nullable=False)

    op.create_unique_constraint("uq_usuario_documento", "usuario", ["documento"])
    op.create_unique_constraint("uq_usuario_usuario", "usuario", ["usuario"])
    op.create_check_constraint(
        "ck_usuario_documento_no_vacio", "usuario", "documento ~ '[^[:space:]]'"
    )
    op.create_check_constraint(
        "ck_usuario_usuario_no_vacio", "usuario", "usuario ~ '[^[:space:]]'"
    )
    op.create_check_constraint(
        "ck_usuario_usuario_normalizado",
        "usuario",
        "usuario = lower(regexp_replace(usuario, '^[[:space:]]+|[[:space:]]+$', '', 'g'))",
    )
    op.create_check_constraint(
        "ck_usuario_rol", "usuario", "rol IN ('ADMINISTRADOR', 'OPERADOR')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_usuario_rol", "usuario", type_="check")
    op.drop_constraint("ck_usuario_usuario_normalizado", "usuario", type_="check")
    op.drop_constraint("ck_usuario_usuario_no_vacio", "usuario", type_="check")
    op.drop_constraint("ck_usuario_documento_no_vacio", "usuario", type_="check")
    op.drop_constraint("uq_usuario_usuario", "usuario", type_="unique")
    op.drop_constraint("uq_usuario_documento", "usuario", type_="unique")

    for column in (
        "actualizado_en",
        "creado_en",
        "direccion",
        "correo",
        "activo",
        "rol",
        "password_hash",
        "usuario",
        "documento",
    ):
        op.drop_column("usuario", column)

    op.execute(
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_usuario_salida TO fk_estancia_operador_salida"
    )
    op.execute(
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_usuario_entrada TO fk_estancia_operador_entrada"
    )
    op.alter_column(
        "estancia",
        "usuario_salida_id",
        new_column_name="operador_salida_id",
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        "estancia",
        "usuario_entrada_id",
        new_column_name="operador_entrada_id",
        existing_type=sa.BigInteger(),
        existing_nullable=False,
    )

    op.execute(
        "ALTER TABLE usuario RENAME CONSTRAINT ck_usuario_telefono_no_vacio TO ck_operador_telefono_no_vacio"
    )
    op.execute(
        "ALTER TABLE usuario RENAME CONSTRAINT ck_usuario_nombre_no_vacio TO ck_operador_nombre_no_vacio"
    )
    op.execute("ALTER TABLE usuario RENAME CONSTRAINT usuario_pkey TO operador_pkey")
    op.rename_table("usuario", "operador")
