"""Modelos iniciales. Importar este módulo no crea tablas ni abre conexiones."""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity, Index, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates


class Base(DeclarativeBase):
    pass


def required_text(value: str, attribute: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{attribute} debe ser texto no vacío.")
    return value.strip()


class Vehiculo(Base):
    __tablename__ = "vehiculo"
    __table_args__ = (
        UniqueConstraint("placa", name="uq_vehiculo_placa"),
        CheckConstraint("placa ~ '[^[:space:]]'", name="ck_vehiculo_placa_no_vacia"),
        CheckConstraint("placa = upper(regexp_replace(placa, '^[[:space:]]+|[[:space:]]+$', '', 'g'))", name="ck_vehiculo_placa_normalizada"),
        CheckConstraint("color ~ '[^[:space:]]'", name="ck_vehiculo_color_no_vacio"),
        CheckConstraint("marca ~ '[^[:space:]]'", name="ck_vehiculo_marca_no_vacia"),
        CheckConstraint("modelo BETWEEN 1 AND 9999", name="ck_vehiculo_modelo_anio"),
        CheckConstraint("tipo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_vehiculo_tipo"),
        CheckConstraint(
            "correo IS NULL OR correo = regexp_replace(correo, '^[[:space:]]+|[[:space:]]+$', '', 'g')",
            name="ck_vehiculo_correo_normalizado",
        ),
        CheckConstraint(
            "avisos_autorizados = (autorizacion_usuario_id IS NOT NULL)",
            name="ck_vehiculo_autorizacion_completa",
        ),
        CheckConstraint(
            "(autorizacion_usuario_id IS NULL) = (autorizacion_fecha_hora IS NULL)",
            name="ck_vehiculo_autorizacion_fecha",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    placa: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False)
    modelo: Mapped[int] = mapped_column(Integer, nullable=False)
    marca: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    correo: Mapped[str | None] = mapped_column(Text, nullable=True)
    avisos_autorizados: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    autorizacion_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id", name="fk_vehiculo_autorizacion_usuario", ondelete="RESTRICT"),
        nullable=True,
    )
    autorizacion_fecha_hora: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @validates("placa", "color", "marca", "tipo")
    def validate_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        if key == "placa":
            return value.upper()
        if key == "tipo" and value not in {"MOTO", "AUTOMOVIL", "CAMIONETA"}:
            raise ValueError("tipo debe ser MOTO, AUTOMOVIL o CAMIONETA.")
        return value

    @validates("modelo")
    def validate_modelo(self, key: str, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 9999:
            raise ValueError("modelo debe ser un año entero entre 1 y 9999.")
        return value

    @validates("correo")
    def validate_correo(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return required_text(value, key).lower()

    pagos: Mapped[list["Pago"]] = relationship(
        back_populates="vehiculo", lazy="selectin", order_by="Pago.fecha_hora"
    )

    @property
    def pagos_activos(self) -> list["Pago"]:
        return [pago for pago in self.pagos if pago.anulacion_fecha_hora is None]

    @property
    def fecha_vencimiento(self) -> date | None:
        """Derivado: max(vencimiento_ciclo) de los pagos activos (RN-VIG-01)."""
        vencimientos = [pago.vencimiento_ciclo for pago in self.pagos_activos]
        return max(vencimientos) if vencimientos else None

    @property
    def dia_corte(self) -> int | None:
        if not self.pagos_activos:
            return None
        ultimo = max(self.pagos_activos, key=lambda pago: (pago.fecha_hora, pago.id or 0))
        return ultimo.dia_corte


class Celda(Base):
    __tablename__ = "celda"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_celda_codigo"),
        CheckConstraint("codigo ~ '[^[:space:]]'", name="ck_celda_codigo_no_vacio"),
        CheckConstraint("codigo = upper(regexp_replace(codigo, '^[[:space:]]+|[[:space:]]+$', '', 'g'))", name="ck_celda_codigo_normalizado"),
        CheckConstraint("tipo ~ '[^[:space:]]'", name="ck_celda_tipo_no_vacio"),
        CheckConstraint("tipo IN ('AUTO', 'MOTO')", name="ck_celda_tipo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    activa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    @validates("codigo", "tipo")
    def validate_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        if key == "codigo":
            return value.upper()
        if value not in {"AUTO", "MOTO"}:
            raise ValueError("tipo debe ser AUTO o MOTO.")
        return value


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("documento", name="uq_usuario_documento"),
        UniqueConstraint("usuario", name="uq_usuario_usuario"),
        CheckConstraint("documento ~ '[^[:space:]]'", name="ck_usuario_documento_no_vacio"),
        CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_usuario_nombre_no_vacio"),
        CheckConstraint("telefono ~ '[^[:space:]]'", name="ck_usuario_telefono_no_vacio"),
        CheckConstraint("usuario ~ '[^[:space:]]'", name="ck_usuario_usuario_no_vacio"),
        CheckConstraint(
            "usuario = lower(regexp_replace(usuario, '^[[:space:]]+|[[:space:]]+$', '', 'g'))",
            name="ck_usuario_usuario_normalizado",
        ),
        CheckConstraint("rol IN ('ADMINISTRADOR', 'OPERADOR')", name="ck_usuario_rol"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    documento: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    correo: Mapped[str | None] = mapped_column(Text, nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @validates("documento", "nombre", "telefono", "usuario", "correo", "direccion")
    def validate_text(self, key: str, value: str | None) -> str | None:
        if value is None:
            if key in {"telefono", "correo", "direccion"}:
                return None
            raise ValueError(f"{key} debe ser texto no vacío.")
        value = required_text(value, key)
        return value.lower() if key == "usuario" else value

    @validates("rol")
    def validate_rol(self, key: str, value: str) -> str:
        if value not in {"ADMINISTRADOR", "OPERADOR"}:
            raise ValueError("rol debe ser ADMINISTRADOR u OPERADOR.")
        return value

    def es_administrador(self) -> bool:
        return self.rol == "ADMINISTRADOR"


class Estancia(Base):
    __tablename__ = "estancia"
    __table_args__ = (
        CheckConstraint("salida >= entrada", name="ck_estancia_orden_fechas"),
        CheckConstraint(
            "(salida IS NULL) = (usuario_salida_id IS NULL)",
            name="ck_estancia_cierre_completo",
        ),
        Index("uq_estancia_vehiculo_abierta", "vehiculo_id", unique=True,
              postgresql_where=text("salida IS NULL")),
        Index("uq_estancia_celda_abierta", "celda_id", unique=True,
              postgresql_where=text("salida IS NULL")),
        Index("ix_estancia_vehiculo_entrada", "vehiculo_id", "entrada"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehiculo.id", name="fk_estancia_vehiculo", ondelete="RESTRICT"), nullable=False
    )
    celda_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("celda.id", name="fk_estancia_celda", ondelete="RESTRICT"), nullable=False
    )
    entrada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    salida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario_entrada_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id", name="fk_estancia_usuario_entrada", ondelete="RESTRICT"), nullable=False
    )
    usuario_salida_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id", name="fk_estancia_usuario_salida", ondelete="RESTRICT"), nullable=True
    )

    vehiculo: Mapped[Vehiculo] = relationship()
    celda: Mapped[Celda] = relationship()
    usuario_entrada: Mapped[Usuario] = relationship(foreign_keys=[usuario_entrada_id])
    usuario_salida: Mapped[Usuario | None] = relationship(foreign_keys=[usuario_salida_id])

    def esta_abierta(self) -> bool:
        return self.salida is None

    def cerrar(self, fecha_salida: datetime, usuario: Usuario) -> None:
        """Valida y asigna el cierre; el servicio debe gestionar flush y commit."""
        if not self.esta_abierta():
            raise ValueError("La estancia ya está cerrada.")
        if not isinstance(fecha_salida, datetime) or fecha_salida.utcoffset() is None:
            raise ValueError("La fecha de salida debe tener zona horaria.")
        if not isinstance(self.entrada, datetime) or self.entrada.utcoffset() is None:
            raise ValueError("La entrada debe estar cargada y tener zona horaria antes de cerrar.")
        if fecha_salida.astimezone(timezone.utc) < self.entrada.astimezone(timezone.utc):
            raise ValueError("La salida no puede ser anterior a la entrada.")
        if not isinstance(usuario, Usuario) or usuario.id is None:
            raise ValueError("El usuario de salida debe tener un id asignado.")
        self.salida = fecha_salida
        self.usuario_salida = usuario
        self.usuario_salida_id = usuario.id


class CambioCelda(Base):
    """Historial append-only de los cambios de celda (S6, D4)."""

    __tablename__ = "cambio_celda"
    __table_args__ = (
        CheckConstraint(
            "celda_anterior_id <> celda_nueva_id",
            name="ck_cambio_celda_celdas_distintas",
        ),
        Index("ix_cambio_celda_fecha_hora", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    estancia_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "estancia.id", name="fk_cambio_celda_estancia", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    celda_anterior_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "celda.id", name="fk_cambio_celda_celda_anterior", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    celda_nueva_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "celda.id", name="fk_cambio_celda_celda_nueva", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id", name="fk_cambio_celda_usuario", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


MOTIVOS_ANULACION = (
    "Error de digitación",
    "Valor incorrecto",
    "Pago duplicado",
    "Recibo no válido",
    "Otro",
)


class Pago(Base):
    """Registro de una mensualidad pagada. No se borra: se anula (RN-ANU-01)."""

    __tablename__ = "pago"
    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_pago_valor_positivo"),
        CheckConstraint("referencia ~ '[^[:space:]]'", name="ck_pago_referencia_no_vacia"),
        CheckConstraint(
            "referencia = regexp_replace(referencia, '^[[:space:]]+|[[:space:]]+$', '', 'g')",
            name="ck_pago_referencia_normalizada",
        ),
        CheckConstraint("dia_corte BETWEEN 1 AND 31", name="ck_pago_dia_corte"),
        CheckConstraint("inicio_ciclo < vencimiento_ciclo", name="ck_pago_ciclo_orden"),
        CheckConstraint(
            "anulacion_motivo IN ('Error de digitación', 'Valor incorrecto', "
            "'Pago duplicado', 'Recibo no válido', 'Otro')",
            name="ck_pago_motivo_anulacion",
        ),
        CheckConstraint(
            "(anulacion_fecha_hora IS NULL) = (anulacion_usuario_id IS NULL) "
            "AND (anulacion_fecha_hora IS NULL) = (anulacion_motivo IS NULL)",
            name="ck_pago_anulacion_completa",
        ),
        Index(
            "uq_pago_referencia_activa",
            "referencia",
            unique=True,
            postgresql_where=text("anulacion_fecha_hora IS NULL"),
        ),
        Index("ix_pago_vehiculo_fecha", "vehiculo_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehiculo.id", name="fk_pago_vehiculo", ondelete="RESTRICT"),
        nullable=False,
    )
    valor: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id", name="fk_pago_usuario", ondelete="RESTRICT"),
        nullable=False,
    )
    dia_corte: Mapped[int] = mapped_column(Integer, nullable=False)
    inicio_ciclo: Mapped[date] = mapped_column(Date, nullable=False)
    vencimiento_ciclo: Mapped[date] = mapped_column(Date, nullable=False)
    anulacion_fecha_hora: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anulacion_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id", name="fk_pago_anulacion_usuario", ondelete="RESTRICT"),
        nullable=True,
    )
    anulacion_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)

    vehiculo: Mapped[Vehiculo] = relationship(back_populates="pagos")
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    anulacion_usuario: Mapped[Usuario | None] = relationship(
        foreign_keys=[anulacion_usuario_id]
    )

    @validates("referencia")
    def validate_referencia(self, key: str, value: str) -> str:
        return required_text(value, key)

    @validates("valor")
    def validate_valor(self, key: str, value: int) -> int:
        if type(value) is not int or value <= 0:
            raise ValueError("valor debe ser un entero positivo.")
        return value

    @validates("dia_corte")
    def validate_dia_corte(self, key: str, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 31:
            raise ValueError("dia_corte debe estar entre 1 y 31.")
        return value

    @validates("anulacion_motivo")
    def validate_motivo(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in MOTIVOS_ANULACION:
            raise ValueError("El motivo de anulación no pertenece al catálogo.")
        return value

    def estado(self) -> str:
        return "ANULADO" if self.anulacion_fecha_hora is not None else "ACTIVO"

    def anular(self, fecha_hora: datetime, usuario: Usuario, motivo: str) -> None:
        if self.estado() == "ANULADO":
            raise ValueError("El pago ya está anulado.")
        self.anulacion_fecha_hora = fecha_hora
        self.anulacion_usuario_id = usuario.id
        self.anulacion_motivo = motivo


class Aviso(Base):
    """Registro de cada aviso de vencimiento enviado por correo (RN-AVI-02)."""

    __tablename__ = "aviso"
    __table_args__ = (
        CheckConstraint("resultado IN ('ENVIADO', 'FALLIDO')", name="ck_aviso_resultado"),
        CheckConstraint("correo ~ '[^[:space:]]'", name="ck_aviso_correo_no_vacio"),
        Index(
            "uq_aviso_enviado",
            "vehiculo_id",
            "fecha_vencimiento",
            unique=True,
            postgresql_where=text("resultado = 'ENVIADO'"),
        ),
        Index("ix_aviso_fecha_hora", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehiculo.id", name="fk_aviso_vehiculo", ondelete="RESTRICT"),
        nullable=False,
    )
    correo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    resultado: Mapped[str] = mapped_column(Text, nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vehiculo: Mapped[Vehiculo] = relationship()

    @validates("resultado")
    def validate_resultado(self, key: str, value: str) -> str:
        if value not in ("ENVIADO", "FALLIDO"):
            raise ValueError("resultado debe ser ENVIADO o FALLIDO.")
        return value

    @validates("correo")
    def validate_correo(self, key: str, value: str) -> str:
        return required_text(value, key).lower()
