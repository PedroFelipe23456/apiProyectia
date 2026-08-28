"""
Esquemas Pydantic: validan lo que entra (Create) y dan forma a lo que
sale (Read) en cada ruta. Cada entidad sigue el mismo patrón Base -> Create -> Read.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


# ---------------- Roles ----------------
class RolBase(BaseModel):
    nombre_rol: str
    descripcion: Optional[str] = None


class RolCreate(RolBase):
    pass


class RolRead(RolBase):
    model_config = ConfigDict(from_attributes=True)
    id_rol: int


# ---------------- Usuarios ----------------
class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    id_rol: int


class UsuarioCreate(UsuarioBase):
    password_hash: str


class UsuarioRead(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id_usuario: int
    fecha_registro: datetime


# ---------------- Ubicaciones ----------------
class UbicacionBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class UbicacionCreate(UbicacionBase):
    pass


class UbicacionRead(UbicacionBase):
    model_config = ConfigDict(from_attributes=True)
    id_ubicacion: int


# ---------------- Tipos de sensor ----------------
class TipoSensorBase(BaseModel):
    modelo: str
    tipo_magnitud: str
    rango_min: Decimal
    rango_max: Decimal
    sensibilidad_mv_por_a: Optional[Decimal] = None


class TipoSensorCreate(TipoSensorBase):
    pass


class TipoSensorRead(TipoSensorBase):
    model_config = ConfigDict(from_attributes=True)
    id_tipo_sensor: int


# ---------------- Unidades de medida ----------------
class UnidadMedidaBase(BaseModel):
    nombre: str
    simbolo: str


class UnidadMedidaCreate(UnidadMedidaBase):
    pass


class UnidadMedidaRead(UnidadMedidaBase):
    model_config = ConfigDict(from_attributes=True)
    id_unidad: int


# ---------------- Tipos de umbral ----------------
class TipoUmbralBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class TipoUmbralCreate(TipoUmbralBase):
    pass


class TipoUmbralRead(TipoUmbralBase):
    model_config = ConfigDict(from_attributes=True)
    id_tipo_umbral: int


# ---------------- Dispositivos ----------------
class DispositivoBase(BaseModel):
    nombre: str
    mac_address: str
    id_ubicacion: int
    fecha_instalacion: date
    estado: str = "activo"


class DispositivoCreate(DispositivoBase):
    pass


class DispositivoRead(DispositivoBase):
    model_config = ConfigDict(from_attributes=True)
    id_dispositivo: int


# ---------------- Sensores ----------------
class SensorBase(BaseModel):
    id_tipo_sensor: int
    id_dispositivo: int
    numero_serie: str
    fecha_calibracion: Optional[date] = None


class SensorCreate(SensorBase):
    pass


class SensorRead(SensorBase):
    model_config = ConfigDict(from_attributes=True)
    id_sensor: int


# ---------------- Componentes eléctricos ----------------
class ComponenteElectricoBase(BaseModel):
    nombre: str
    tipo_componente: str
    voltaje_nominal_v: Decimal
    potencia_nominal_w: Decimal
    id_sensor: int


class ComponenteElectricoCreate(ComponenteElectricoBase):
    pass


class ComponenteElectricoRead(ComponenteElectricoBase):
    model_config = ConfigDict(from_attributes=True)
    id_componente: int


# ---------------- Mediciones ----------------
class MedicionBase(BaseModel):
    id_componente: int
    corriente_a: Decimal
    voltaje_v: Decimal
    potencia_w: Decimal
    energia_kwh: Decimal


class MedicionCreate(MedicionBase):
    pass


class MedicionRead(MedicionBase):
    model_config = ConfigDict(from_attributes=True)
    id_medicion: int
    fecha_hora: datetime


# ---------------- Umbrales de alerta ----------------
class UmbralAlertaBase(BaseModel):
    id_componente: int
    id_tipo_umbral: int
    id_unidad: int
    valor_limite: Decimal


class UmbralAlertaCreate(UmbralAlertaBase):
    pass


class UmbralAlertaRead(UmbralAlertaBase):
    model_config = ConfigDict(from_attributes=True)
    id_umbral: int


# ---------------- Alertas ----------------
class AlertaBase(BaseModel):
    id_medicion: int
    id_umbral: int
    mensaje: str
    nivel_severidad: str
    estado: str = "nueva"


class AlertaCreate(AlertaBase):
    pass


class AlertaRead(AlertaBase):
    model_config = ConfigDict(from_attributes=True)
    id_alerta: int
    fecha_hora: datetime


# ---------------- Reportes ----------------
class ReporteBase(BaseModel):
    id_usuario: int
    fecha_inicio: date
    fecha_fin: date
    ruta_archivo: str
    tipo_reporte: str


class ReporteCreate(ReporteBase):
    pass


class ReporteRead(ReporteBase):
    model_config = ConfigDict(from_attributes=True)
    id_reporte: int
    fecha_generacion: datetime


# ---------------- Reporte - Detalle ----------------
class ReporteDetalleBase(BaseModel):
    id_reporte: int
    id_medicion: int


class ReporteDetalleCreate(ReporteDetalleBase):
    pass


class ReporteDetalleRead(ReporteDetalleBase):
    model_config = ConfigDict(from_attributes=True)
