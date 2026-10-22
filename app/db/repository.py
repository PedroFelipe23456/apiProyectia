"""
Capa de repositorios (patrón Repository).

BaseRepository centraliza las operaciones CRUD comunes a cualquier
entidad usando Genéricos de Python. Cada entidad tiene su propio
repositorio que HEREDA de BaseRepository y solo agrega los métodos
propios de su dominio.
"""
import requests
from datetime import datetime
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.orm import Session
from app.db import models

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def get_by_id(self, id_value, pk_field: str) -> Optional[ModelType]:
        return (
            self.db.query(self.model)
            .filter(getattr(self.model, pk_field) == id_value)
            .first()
        )

    def create(self, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ModelType, obj_in: dict) -> ModelType:
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, db_obj: ModelType) -> None:
        self.db.delete(db_obj)
        self.db.commit()


class RolRepository(BaseRepository[models.Rol]):
    def __init__(self, db: Session):
        super().__init__(models.Rol, db)

    def get_by_nombre(self, nombre: str) -> Optional[models.Rol]:
        return self.db.query(models.Rol).filter(models.Rol.nombre_rol == nombre).first()


class UsuarioRepository(BaseRepository[models.Usuario]):
    def __init__(self, db: Session):
        super().__init__(models.Usuario, db)

    def get_by_email(self, email: str) -> Optional[models.Usuario]:
        return self.db.query(models.Usuario).filter(models.Usuario.email == email).first()


class UbicacionRepository(BaseRepository[models.Ubicacion]):
    def __init__(self, db: Session):
        super().__init__(models.Ubicacion, db)


class TipoSensorRepository(BaseRepository[models.TipoSensor]):
    def __init__(self, db: Session):
        super().__init__(models.TipoSensor, db)


class UnidadMedidaRepository(BaseRepository[models.UnidadMedida]):
    def __init__(self, db: Session):
        super().__init__(models.UnidadMedida, db)


class TipoUmbralRepository(BaseRepository[models.TipoUmbral]):
    def __init__(self, db: Session):
        super().__init__(models.TipoUmbral, db)


class DispositivoRepository(BaseRepository[models.Dispositivo]):
    def __init__(self, db: Session):
        super().__init__(models.Dispositivo, db)

    def get_by_estado(self, estado: str) -> List[models.Dispositivo]:
        return (
            self.db.query(models.Dispositivo)
            .filter(models.Dispositivo.estado == estado)
            .all()
        )


class SensorRepository(BaseRepository[models.Sensor]):
    def __init__(self, db: Session):
        super().__init__(models.Sensor, db)


class ComponenteElectricoRepository(BaseRepository[models.ComponenteElectrico]):
    def __init__(self, db: Session):
        super().__init__(models.ComponenteElectrico, db)


class MedicionRepository(BaseRepository[models.Medicion]):
    def __init__(self, db: Session):
        super().__init__(models.Medicion, db)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[models.Medicion]:
        """
        Obtiene las mediciones almacenadas directamente en PostgreSQL (Neon).
        """
        return (
            self.db.query(models.Medicion)
            .order_by(models.Medicion.fecha_hora.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_componente(self, id_componente: int, limit: int = 100) -> List[models.Medicion]:
        return (
            self.db.query(models.Medicion)
            .filter(models.Medicion.id_componente == id_componente)
            .order_by(models.Medicion.fecha_hora.desc())
            .limit(limit)
            .all()
        )


class UmbralAlertaRepository(BaseRepository[models.UmbralAlerta]):
    def __init__(self, db: Session):
        super().__init__(models.UmbralAlerta, db)


class AlertaRepository(BaseRepository[models.Alerta]):
    def __init__(self, db: Session):
        super().__init__(models.Alerta, db)

    def get_por_estado(self, estado: str) -> List[models.Alerta]:
        return self.db.query(models.Alerta).filter(models.Alerta.estado == estado).all()


class ReporteRepository(BaseRepository[models.Reporte]):
    def __init__(self, db: Session):
        super().__init__(models.Reporte, db)