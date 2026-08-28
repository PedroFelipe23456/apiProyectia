"""
Modelos ORM (SQLAlchemy) - reflejan 1 a 1 las tablas de taller1_basedatos.sql
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Numeric, Date, DateTime,
    ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Rol(Base):
    __tablename__ = "roles"
    id_rol = Column(Integer, primary_key=True)
    nombre_rol = Column(String(50), nullable=False, unique=True)
    descripcion = Column(String(255))

    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    id_rol = Column(Integer, ForeignKey("roles.id_rol"), nullable=False)
    fecha_registro = Column(DateTime, server_default=func.now())

    rol = relationship("Rol", back_populates="usuarios")
    reportes = relationship("Reporte", back_populates="usuario")


class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    id_ubicacion = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255))

    dispositivos = relationship("Dispositivo", back_populates="ubicacion")


class TipoSensor(Base):
    __tablename__ = "tipos_sensor"
    id_tipo_sensor = Column(Integer, primary_key=True)
    modelo = Column(String(50), nullable=False, unique=True)
    tipo_magnitud = Column(String(30), nullable=False)
    rango_min = Column(Numeric(8, 2), nullable=False)
    rango_max = Column(Numeric(8, 2), nullable=False)
    sensibilidad_mv_por_a = Column(Numeric(6, 2))

    sensores = relationship("Sensor", back_populates="tipo_sensor")


class UnidadMedida(Base):
    __tablename__ = "unidades_medida"
    id_unidad = Column(Integer, primary_key=True)
    nombre = Column(String(40), nullable=False)
    simbolo = Column(String(10), nullable=False, unique=True)


class TipoUmbral(Base):
    __tablename__ = "tipos_umbral"
    id_tipo_umbral = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False, unique=True)
    descripcion = Column(String(255))


class Dispositivo(Base):
    __tablename__ = "dispositivos"
    id_dispositivo = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    mac_address = Column(String(17), nullable=False, unique=True)
    id_ubicacion = Column(Integer, ForeignKey("ubicaciones.id_ubicacion"), nullable=False)
    fecha_instalacion = Column(Date, nullable=False)
    estado = Column(String(20), nullable=False, default="activo")

    ubicacion = relationship("Ubicacion", back_populates="dispositivos")
    sensores = relationship("Sensor", back_populates="dispositivo")


class Sensor(Base):
    __tablename__ = "sensores"
    id_sensor = Column(Integer, primary_key=True)
    id_tipo_sensor = Column(Integer, ForeignKey("tipos_sensor.id_tipo_sensor"), nullable=False)
    id_dispositivo = Column(Integer, ForeignKey("dispositivos.id_dispositivo"), nullable=False)
    numero_serie = Column(String(50), nullable=False, unique=True)
    fecha_calibracion = Column(Date)

    tipo_sensor = relationship("TipoSensor", back_populates="sensores")
    dispositivo = relationship("Dispositivo", back_populates="sensores")
    componentes = relationship("ComponenteElectrico", back_populates="sensor")


class ComponenteElectrico(Base):
    __tablename__ = "componentes_electricos"
    id_componente = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    tipo_componente = Column(String(50), nullable=False)
    voltaje_nominal_v = Column(Numeric(6, 2), nullable=False)
    potencia_nominal_w = Column(Numeric(8, 2), nullable=False)
    id_sensor = Column(Integer, ForeignKey("sensores.id_sensor"), nullable=False)

    sensor = relationship("Sensor", back_populates="componentes")
    mediciones = relationship("Medicion", back_populates="componente")
    umbrales = relationship("UmbralAlerta", back_populates="componente")


class Medicion(Base):
    __tablename__ = "mediciones"
    id_medicion = Column(BigInteger, primary_key=True)
    id_componente = Column(Integer, ForeignKey("componentes_electricos.id_componente"), nullable=False)
    corriente_a = Column(Numeric(8, 3), nullable=False)
    voltaje_v = Column(Numeric(8, 2), nullable=False)
    potencia_w = Column(Numeric(10, 2), nullable=False)
    energia_kwh = Column(Numeric(10, 4), nullable=False)
    fecha_hora = Column(DateTime, server_default=func.now())

    componente = relationship("ComponenteElectrico", back_populates="mediciones")
    alertas = relationship("Alerta", back_populates="medicion")


class UmbralAlerta(Base):
    __tablename__ = "umbrales_alerta"
    id_umbral = Column(Integer, primary_key=True)
    id_componente = Column(Integer, ForeignKey("componentes_electricos.id_componente"), nullable=False)
    id_tipo_umbral = Column(Integer, ForeignKey("tipos_umbral.id_tipo_umbral"), nullable=False)
    id_unidad = Column(Integer, ForeignKey("unidades_medida.id_unidad"), nullable=False)
    valor_limite = Column(Numeric(10, 2), nullable=False)

    componente = relationship("ComponenteElectrico", back_populates="umbrales")
    alertas = relationship("Alerta", back_populates="umbral")


class Alerta(Base):
    __tablename__ = "alertas"
    id_alerta = Column(Integer, primary_key=True)
    id_medicion = Column(BigInteger, ForeignKey("mediciones.id_medicion"), nullable=False)
    id_umbral = Column(Integer, ForeignKey("umbrales_alerta.id_umbral"), nullable=False)
    mensaje = Column(String(255), nullable=False)
    nivel_severidad = Column(String(20), nullable=False)
    fecha_hora = Column(DateTime, server_default=func.now())
    estado = Column(String(20), nullable=False, default="nueva")

    medicion = relationship("Medicion", back_populates="alertas")
    umbral = relationship("UmbralAlerta", back_populates="alertas")


class Reporte(Base):
    __tablename__ = "reportes"
    id_reporte = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha_generacion = Column(DateTime, server_default=func.now())
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    ruta_archivo = Column(String(255), nullable=False)
    tipo_reporte = Column(String(30), nullable=False)

    usuario = relationship("Usuario", back_populates="reportes")
    detalles = relationship("ReporteDetalle", back_populates="reporte")


class ReporteDetalle(Base):
    __tablename__ = "reporte_detalle"
    id_reporte = Column(Integer, ForeignKey("reportes.id_reporte"), primary_key=True)
    id_medicion = Column(BigInteger, ForeignKey("mediciones.id_medicion"), primary_key=True)

    reporte = relationship("Reporte", back_populates="detalles")
