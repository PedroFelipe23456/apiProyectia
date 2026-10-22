"""
Lecturas en tiempo real del medidor.

El ESP32 manda voltaje, corriente y potencia cada ~1 s en GET /motor/?v=..&i=..&p=..
Aquí se guardan en memoria las últimas MAX_PUNTOS para que la web dibuje las
gráficas en vivo. No van a la base de datos (serían 3600 filas por hora);
para guardar una medición se sigue usando POST /mediciones/.
Si el servidor reinicia, el historial en vivo empieza vacío.
"""
import threading
import time
from collections import deque
from typing import List

from pydantic import BaseModel

MAX_PUNTOS = 300  # unos 5 minutos a 1 lectura por segundo


class PuntoVivo(BaseModel):
    ts: float          # momento de la lectura, en milisegundos desde 1970 (UTC)
    voltaje_v: float
    corriente_a: float
    potencia_w: float


_lock = threading.Lock()
_puntos: deque = deque(maxlen=MAX_PUNTOS)


def registrar(voltaje_v: float, corriente_ma: float, potencia_w: float) -> None:
    with _lock:
        _puntos.append(PuntoVivo(
            ts=time.time() * 1000,
            voltaje_v=voltaje_v,
            corriente_a=corriente_ma / 1000,
            potencia_w=potencia_w,
        ))


def ultimos(n: int) -> List[PuntoVivo]:
    with _lock:
        return list(_puntos)[-n:]
