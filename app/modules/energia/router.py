"""
Módulo Energía: mediciones de voltaje, corriente y potencia del ESP32 + ACS712.

- POST /mediciones/            el ESP32 guarda una medición (botón 2 / tecla del menú).
- GET  /mediciones/            el dashboard y el LCD leen el historial (más reciente primero).
- GET  /mediciones/resumen     estadísticas para las tarjetas del dashboard.
- GET  /mediciones/desviacion  opción 9 del menú del LCD: {"resultado": "..."}.
"""
import statistics
import traceback
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import schemas
from app.db.repository import MedicionRepository

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


@router.get("/desviacion")
def desviacion(limit: int = 500, db: Session = Depends(get_db)):
    """Desviación estándar de la potencia. El LCD muestra los primeros 16 caracteres."""
    potencias = [float(m.potencia_w) for m in _ultimas(db, limit)]
    if len(potencias) < 2:
        return {"resultado": "Pocos registros"}
    return {"resultado": f"SD: {statistics.pstdev(potencias):.2f} W"}
