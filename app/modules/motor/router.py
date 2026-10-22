"""
Módulo Motor: control de velocidad y dirección del motor DC (ESP32 + L298N).

- GET /motor/         lo usa el ESP32 cada 1 s. Devuelve el estado deseado y registra
                      el contacto. Puede traer ?v=..&i=..&p=.. con los valores del LCD.
- PUT /motor/         lo usa la web. Pydantic valida velocidad 0-100 y dirección.
- GET /motor/estado   lo usa la web: estado, conexión del ESP32 y última lectura en vivo.

El estado vive en memoria: si el servidor reinicia, vuelve a "stop" (es lo seguro).
"""
import threading
import time
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.modules.energia import vivo

router = APIRouter(prefix="/motor", tags=["Motor"])

# Si el ESP32 no consulta en este tiempo, la web lo muestra como desconectado.
SEGUNDOS_CONECTADO = 5


class EstadoMotor(BaseModel):
    """Lo que la web envía y lo que el ESP32 recibe."""

    velocidad: int = Field(ge=0, le=100, description="Porcentaje 0-100")
    direccion: Literal["adelante", "atras", "stop"]


class LecturaEnVivo(BaseModel):
    """Lo que muestra el LCD en este momento (no se guarda en la base de datos)."""

    voltaje_v: float
    corriente_ma: float
    potencia_w: float


class EstadoCompleto(EstadoMotor):
    conectado: bool
    segundos_desde_contacto: Optional[float]
    lectura: Optional[LecturaEnVivo]


# El lock evita que dos peticiones a la vez dejen el estado a medias.
_lock = threading.Lock()
_estado = EstadoMotor(velocidad=0, direccion="stop")
_ultimo_contacto: Optional[float] = None  # time.monotonic() del último GET del ESP32
_lectura: Optional[LecturaEnVivo] = None


@router.get("/", response_model=EstadoMotor)
def leer_motor(
    v: Optional[float] = None,
    i: Optional[float] = None,
    p: Optional[float] = None,
) -> EstadoMotor:
    """Lo usa el ESP32: v = voltaje (V), i = corriente (mA), p = potencia (W)."""
    global _ultimo_contacto, _lectura
    with _lock:
        _ultimo_contacto = time.monotonic()
        if v is not None and i is not None and p is not None:
            _lectura = LecturaEnVivo(voltaje_v=v, corriente_ma=i, potencia_w=p)
            vivo.registrar(v, i, p)  # para las gráficas en tiempo real
        return _estado


@router.put("/", response_model=EstadoMotor)
def cambiar_motor(nuevo: EstadoMotor) -> EstadoMotor:
    """Lo usa la web. Si los datos no son válidos, FastAPI responde 422."""
    global _estado
    with _lock:
        _estado = nuevo
        return _estado


@router.get("/estado", response_model=EstadoCompleto)
def leer_estado() -> EstadoCompleto:
    with _lock:
        segundos = None if _ultimo_contacto is None else time.monotonic() - _ultimo_contacto
        return EstadoCompleto(
            **_estado.model_dump(),
            conectado=segundos is not None and segundos < SEGUNDOS_CONECTADO,
            segundos_desde_contacto=None if segundos is None else round(segundos, 1),
            lectura=_lectura,
        )
