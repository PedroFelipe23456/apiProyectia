"""
Esquemas Pydantic: validan lo que entra (Create) y dan forma a lo que
sale (Read) en cada ruta. Cada entidad sigue el mismo patrón Base -> Create -> Read.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


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
    id_componente: int = 1
    corriente_a: Union[float, Decimal, str]
    voltaje_v: Union[float, Decimal, str]
    potencia_w: Union[float, Decimal, str]
    energia_kwh: Union[float, Decimal, str]


class MedicionCreate(MedicionBase):
    pass


class MedicionRead(MedicionBase):
    model_config = ConfigDict(from_attributes=True)
    id_medicion: int
    fecha_hora: Union[datetime, str]

    @field_validator('corriente_a', 'voltaje_v', 'potencia_w', 'energia_kwh', mode='before')
    @classmethod
    def normalizar_flotante(cls, v):
        if v is None:
            return 0.0
        try:
            # Extrae el número flotante limpio sin notaciones de ceros infladas
            s = str(v).strip()
            if s.replace('.', '', 1).replace('-', '', 1).isdigit():
                val = float(s)
                # Si el valor viene absurdamente inflado por InfluxDB, tomar significativos
                if abs(val) > 10000 and '.' in s:
                    p = s.split('.')
                    val = float(p[0][-3:] + '.' + p[1][:2])
                # 4 decimales: la energía (kWh) por registro es muy pequeña
                return round(val, 4)
            return float(v)
        except Exception:
            return 0.0


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