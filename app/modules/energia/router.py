"""
Módulo Energía: mediciones de voltaje, corriente y potencia del ESP32 + ACS712.

- POST /mediciones/            el ESP32 guarda una medición (botón 2 / tecla del menú).
- GET  /mediciones/            el dashboard y el LCD leen el historial (más reciente primero).
- GET  /mediciones/resumen     estadísticas para las tarjetas del dashboard.
- GET  /mediciones/desviacion  opción 9 del menú del LCD: {"resultado": "..."}.
- GET  /mediciones/vivo        últimas lecturas en tiempo real (memoria, ~1 por segundo).

Menú del teclado HX-543 (opciones que consultan la base de datos). Cada una responde
{"resultado": "..."} con un texto de máximo 16 caracteres, listo para el LCD:
- GET  /mediciones/ultimo          opción 2: último registro guardado
- GET  /mediciones/promedio-24h    opción 3: potencia promedio de las últimas 24 h
- GET  /mediciones/maxmin-24h      opción 4: potencia máxima y mínima de las últimas 24 h
- GET  /mediciones/promedio-hora   opción 5: potencia promedio de la última hora
- GET  /mediciones/registros-24h   opción 6: cantidad de registros de las últimas 24 h
- GET  /mediciones/desviacion      opción 9: desviación estándar de la potencia, últimas 24 h
- GET  /mediciones/menu            todo lo anterior en un solo JSON (lo usa la web)
"""
import statistics
import traceback
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import models, schemas
from app.db.repository import MedicionRepository
from app.modules.energia import vivo

router = APIRouter(prefix="/mediciones", tags=["Mediciones"])


class ResumenMediciones(BaseModel):
    total: int
    potencia_promedio_w: Optional[float]
    potencia_max_w: Optional[float]
    potencia_min_w: Optional[float]
    voltaje_promedio_v: Optional[float]
    corriente_promedio_a: Optional[float]
    energia_total_kwh: Optional[float]


def _ultimas(db: Session, limit: int):
    return MedicionRepository(db).get_all(skip=0, limit=limit)


@router.get("/", response_model=List[schemas.MedicionRead])
def obtener_mediciones(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Mediciones guardadas en PostgreSQL (Neon), de la más reciente a la más antigua."""
    try:
        return MedicionRepository(db).get_all(skip=skip, limit=limit)
    except Exception:
        print("\n--- ERROR CONSULTANDO POSTGRESQL (NEON) ---")
        traceback.print_exc()
        print("-------------------------------------------\n")
        return []


@router.post("/", response_model=schemas.MedicionRead, status_code=201)
def crear_medicion(item: schemas.MedicionCreate, db: Session = Depends(get_db)):
    """Lo usa el ESP32 (enviarMedicionAPI en el sketch)."""
    try:
        return MedicionRepository(db).create(item.model_dump())
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="No se pudo guardar la medición")


@router.get("/vivo", response_model=List[vivo.PuntoVivo])
def lecturas_en_vivo(n: int = Query(120, ge=1, le=vivo.MAX_PUNTOS)):
    """Las últimas `n` lecturas que mandó el ESP32, de la más antigua a la más reciente."""
    return vivo.ultimos(n)


@router.get("/resumen", response_model=ResumenMediciones)
def resumen(limit: int = 500, db: Session = Depends(get_db)):
    """Promedios, máximos y mínimos sobre las últimas `limit` mediciones."""
    datos = _ultimas(db, limit)
    if not datos:
        return ResumenMediciones(
            total=0, potencia_promedio_w=None, potencia_max_w=None, potencia_min_w=None,
            voltaje_promedio_v=None, corriente_promedio_a=None, energia_total_kwh=None,
        )
    potencias = [float(m.potencia_w) for m in datos]
    return ResumenMediciones(
        total=len(datos),
        potencia_promedio_w=round(statistics.fmean(potencias), 2),
        potencia_max_w=round(max(potencias), 2),
        potencia_min_w=round(min(potencias), 2),
        voltaje_promedio_v=round(statistics.fmean(float(m.voltaje_v) for m in datos), 2),
        corriente_promedio_a=round(statistics.fmean(float(m.corriente_a) for m in datos), 3),
        energia_total_kwh=round(sum(float(m.energia_kwh) for m in datos), 4),
    )


# ---------------- Menú del teclado ----------------
class EstadisticaVentana(BaseModel):
    registros: int
    promedio_w: Optional[float]
    max_w: Optional[float]
    min_w: Optional[float]


class MenuTeclado(BaseModel):
    ultimo: Optional[schemas.MedicionRead]
    ultimas_24h: EstadisticaVentana
    ultima_hora: EstadisticaVentana
    desviacion_w: Optional[float]


def _ahora_bd(db: Session) -> datetime:
    """Hora actual según la base de datos, para comparar con fecha_hora (que pone la BD)."""
    ahora = db.query(func.now()).scalar()
    if isinstance(ahora, str):  # SQLite devuelve texto
        ahora = datetime.fromisoformat(ahora)
    return ahora.replace(tzinfo=None)


def _ventana(db: Session, horas: int) -> EstadisticaVentana:
    M = models.Medicion
    desde = _ahora_bd(db) - timedelta(hours=horas)
    total, prom, maximo, minimo = (
        db.query(func.count(M.id_medicion), func.avg(M.potencia_w), func.max(M.potencia_w), func.min(M.potencia_w))
        .filter(M.fecha_hora >= desde)
        .one()
    )
    r = lambda x: None if x is None else round(float(x), 2)
    return EstadisticaVentana(registros=total or 0, promedio_w=r(prom), max_w=r(maximo), min_w=r(minimo))


def _desviacion(db: Session, horas: int = 24) -> Optional[float]:
    """Desviación estándar de la potencia en la misma ventana que las opciones 3, 4 y 6."""
    M = models.Medicion
    desde = _ahora_bd(db) - timedelta(hours=horas)
    potencias = [float(p) for (p,) in db.query(M.potencia_w).filter(M.fecha_hora >= desde).all()]
    return round(statistics.pstdev(potencias), 2) if len(potencias) >= 2 else None


def _lcd(texto: str) -> dict:
    return {"resultado": texto[:16]}


@router.get("/ultimo")
def menu_ultimo(db: Session = Depends(get_db)):
    """Opción 2 del teclado."""
    datos = _ultimas(db, 1)
    if not datos:
        return _lcd("Sin registros")
    m = datos[0]
    return _lcd(f"V:{float(m.voltaje_v):.1f}V P:{float(m.potencia_w):.2f}W")


@router.get("/promedio-24h")
def menu_promedio_24h(db: Session = Depends(get_db)):
    """Opción 3 del teclado."""
    v = _ventana(db, 24)
    return _lcd("Sin registros" if not v.registros else f"Prom: {v.promedio_w:.2f} W")


@router.get("/maxmin-24h")
def menu_maxmin_24h(db: Session = Depends(get_db)):
    """Opción 4 del teclado."""
    v = _ventana(db, 24)
    return _lcd("Sin registros" if not v.registros else f"Mx:{v.max_w:.1f} Mn:{v.min_w:.1f}W")


@router.get("/promedio-hora")
def menu_promedio_hora(db: Session = Depends(get_db)):
    """Opción 5 del teclado."""
    v = _ventana(db, 1)
    return _lcd("Sin registros 1h" if not v.registros else f"Prom H: {v.promedio_w:.2f} W")


@router.get("/registros-24h")
def menu_registros_24h(db: Session = Depends(get_db)):
    """Opción 6 del teclado."""
    return _lcd(f"Total: {_ventana(db, 24).registros} regs")


@router.get("/desviacion")
def desviacion(db: Session = Depends(get_db)):
    """Opción 9 del teclado: desviación estándar de la potencia de las últimas 24 h."""
    d = _desviacion(db)
    return _lcd("Pocos registros" if d is None else f"SD: {d:.2f} W")


@router.get("/menu", response_model=MenuTeclado)
def menu_completo(db: Session = Depends(get_db)):
    """Los mismos datos de las opciones 2-6 y 9, para mostrarlos en la web."""
    datos = _ultimas(db, 1)
    return MenuTeclado(
        ultimo=datos[0] if datos else None,
        ultimas_24h=_ventana(db, 24),
        ultima_hora=_ventana(db, 1),
        desviacion_w=_desviacion(db),
    )
