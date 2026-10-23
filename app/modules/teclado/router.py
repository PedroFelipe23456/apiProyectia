"""
Módulo Teclado: el teclado HX-543 en la web (por ejemplo desde el celular).

- POST /teclado/          la web envía una tecla. Queda en cola para el ESP32 y la
                          respuesta trae lo que debe mostrar el LCD (2 líneas de 16).
- GET  /teclado/estado    la web consulta si el ESP32 ya ejecutó las teclas enviadas.

El ESP32 no hace peticiones extra: en su consulta de cada segundo (GET /motor/)
recibe el campo "tecla" con la siguiente tecla pendiente y la ejecuta como si
se hubiera pulsado en el teclado físico (ver tomar_tecla()).
"""
import threading
import time
from collections import deque
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.energia import router as energia
from app.modules.energia import vivo

router = APIRouter(prefix="/teclado", tags=["Teclado"])

Tecla = Literal["1", "2", "3", "A", "4", "5", "6", "B", "7", "8", "9", "C", "*", "0", "#", "D"]

MAX_PENDIENTES = 10       # si el ESP32 está desconectado, no se acumulan más de 10 teclas
SEGUNDOS_CADUCIDAD = 60   # una tecla que el ESP32 no recogió en 1 min se descarta
UMBRAL_ALERTA_W = 15.0    # el mismo de la opción 7 del sketch


class PulsacionWeb(BaseModel):
    tecla: Tecla


class Pantalla(BaseModel):
    linea1: str
    linea2: str


class TeclaEnviada(Pantalla):
    id: int
    tecla: str
    pendientes: int


class EstadoTeclado(BaseModel):
    pendientes: List[int]           # id de las teclas que el ESP32 aún no ha recogido
    ultima_ejecutada: Optional[int]  # id de la última tecla que el ESP32 recogió


_lock = threading.Lock()
_cola: deque = deque(maxlen=MAX_PENDIENTES)   # (id, tecla, momento)
_siguiente_id = 1
_ultima_ejecutada: Optional[int] = None
_leds_encendidos = False  # copia del estado de la tecla 0 (solo cuenta las pulsaciones de la web)


def tomar_tecla() -> Optional[str]:
    """La llama GET /motor/: entrega al ESP32 la tecla pendiente más antigua."""
    global _ultima_ejecutada
    with _lock:
        ahora = time.monotonic()
        while _cola and ahora - _cola[0][2] > SEGUNDOS_CADUCIDAD:
            _cola.popleft()
        if not _cola:
            return None
        id_, tecla, _ = _cola.popleft()
        _ultima_ejecutada = id_
        return tecla


def _lcd(t: str) -> str:
    return t[:16]


def _pantalla(tecla: str, db: Session) -> Pantalla:
    """Lo mismo que muestra el LCD del ESP32 para cada opción del menú."""
    global _leds_encendidos
    ultima = vivo.ultimos(1)
    lectura = ultima[0] if ultima else None
    sin_lectura = Pantalla(linea1="", linea2="Sin lectura ESP32")

    if tecla == "1":
        if not lectura:
            return Pantalla(linea1="1.Valor Actual:", linea2=sin_lectura.linea2)
        return Pantalla(linea1="1.Valor Actual:",
                        linea2=_lcd(f"V:{lectura.voltaje_v:.1f}V I:{lectura.corriente_a * 1000:.0f}mA"))
    consultas = {
        "2": ("2. Ultimo Reg:", energia.menu_ultimo),
        "3": ("3. Promed. 24h:", energia.menu_promedio_24h),
        "4": ("4.Max/Min 24h:", energia.menu_maxmin_24h),
        "5": ("5.Prom Ult Hora:", energia.menu_promedio_hora),
        "6": ("6.Registros 24h:", energia.menu_registros_24h),
        "9": ("9.Desv Estandar:", energia.desviacion),
    }
    if tecla in consultas:
        titulo, funcion = consultas[tecla]
        return Pantalla(linea1=titulo, linea2=funcion(db=db)["resultado"])
    if tecla == "7":
        if not lectura:
            return Pantalla(linea1="7. Alerta Umbral", linea2=sin_lectura.linea2)
        alerta = lectura.potencia_w > UMBRAL_ALERTA_W
        return Pantalla(linea1="7. Alerta Umbral", linea2="SOBRECARGA >15W" if alerta else "POTENCIA NORMAL")
    if tecla == "8":
        if not lectura:
            return Pantalla(linea1="8.Pot. Aparente:", linea2=sin_lectura.linea2)
        p = lectura.potencia_w
        return Pantalla(linea1="8.Pot. Aparente:", linea2=_lcd(f"P:{p:.2f}W / {p * 1.1:.1f}VA"))
    if tecla == "0":
        _leds_encendidos = not _leds_encendidos
        return Pantalla(linea1="0. Control LED", linea2="LEDs: ENCENDIDOS" if _leds_encendidos else "LEDs: APAGADOS")
    if tecla == "A":
        return Pantalla(linea1="Enviando API...", linea2="Guardando medic.")
    if tecla == "B":
        return Pantalla(linea1="B.Calibrar cero", linea2="Sin carga/motor")
    return Pantalla(linea1="Opcion Teclado:", linea2=f"Tecla [{tecla}] activa")


@router.post("/", response_model=TeclaEnviada, status_code=201)
def enviar_tecla(p: PulsacionWeb, db: Session = Depends(get_db)) -> TeclaEnviada:
    global _siguiente_id
    pantalla = _pantalla(p.tecla, db)
    with _lock:
        id_ = _siguiente_id
        _siguiente_id += 1
        _cola.append((id_, p.tecla, time.monotonic()))
        pendientes = len(_cola)
    return TeclaEnviada(id=id_, tecla=p.tecla, pendientes=pendientes, **pantalla.model_dump())


@router.get("/estado", response_model=EstadoTeclado)
def estado_teclado() -> EstadoTeclado:
    with _lock:
        return EstadoTeclado(pendientes=[c[0] for c in _cola], ultima_ejecutada=_ultima_ejecutada)
