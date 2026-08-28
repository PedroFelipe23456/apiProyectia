"""
reporte_detalle tiene llave primaria compuesta (id_reporte, id_medicion),
por lo que no encaja en el CRUDRouter genérico (pensado para PK simple)
y se implementa aparte.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/reporte-detalle", tags=["Reporte - Detalle"])


@router.get("/", response_model=list[schemas.ReporteDetalleRead])
def listar(db: Session = Depends(get_db)):
    return db.query(models.ReporteDetalle).all()


@router.get("/{id_reporte}/{id_medicion}", response_model=schemas.ReporteDetalleRead)
def obtener(id_reporte: int, id_medicion: int, db: Session = Depends(get_db)):
    obj = (
        db.query(models.ReporteDetalle)
        .filter_by(id_reporte=id_reporte, id_medicion=id_medicion)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return obj


@router.post("/", response_model=schemas.ReporteDetalleRead, status_code=201)
def crear(item: schemas.ReporteDetalleCreate, db: Session = Depends(get_db)):
    db_obj = models.ReporteDetalle(**item.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/{id_reporte}/{id_medicion}", status_code=204)
def eliminar(id_reporte: int, id_medicion: int, db: Session = Depends(get_db)):
    obj = (
        db.query(models.ReporteDetalle)
        .filter_by(id_reporte=id_reporte, id_medicion=id_medicion)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(obj)
    db.commit()
