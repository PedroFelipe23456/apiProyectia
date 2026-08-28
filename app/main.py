"""
API Taller 1 - Medición de potencia eléctrica con sensor ACS712
FastAPI + SQLAlchemy, estructurada en POO:
  models.py      -> Entidades ORM (una clase por tabla)
  schemas.py     -> Validación de entrada/salida (Pydantic)
  repository.py  -> BaseRepository genérico + un repositorio por entidad (herencia)
  crud_router.py -> CRUDRouter genérico que arma las rutas REST de cada entidad

Ejecutar con:  uvicorn app.main:app --reload
Documentación interactiva en:  http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI

from app import models, schemas
from app.crud_router import CRUDRouter
from app.reporte_detalle_router import router as reporte_detalle_router
from app.repository import (
    RolRepository,
    UsuarioRepository,
    UbicacionRepository,
    TipoSensorRepository,
    UnidadMedidaRepository,
    TipoUmbralRepository,
    DispositivoRepository,
    SensorRepository,
    ComponenteElectricoRepository,
    MedicionRepository,
    UmbralAlertaRepository,
    AlertaRepository,
    ReporteRepository,
)

app = FastAPI(
    title="API Taller 1 - Medición de Potencia (ACS712)",
    description="API REST en POO (FastAPI + SQLAlchemy) para el sistema de "
                 "monitoreo de potencia eléctrica del Taller 1 - IA 2026-2.",
    version="1.0.0",
)

# (prefijo, etiquetas, esquema de creación, esquema de lectura, repositorio, nombre de PK)
RUTAS = [
    ("/roles", ["Roles"], schemas.RolCreate, schemas.RolRead, RolRepository, "id_rol"),
    ("/usuarios", ["Usuarios"], schemas.UsuarioCreate, schemas.UsuarioRead, UsuarioRepository, "id_usuario"),
    ("/ubicaciones", ["Ubicaciones"], schemas.UbicacionCreate, schemas.UbicacionRead, UbicacionRepository, "id_ubicacion"),
    ("/tipos-sensor", ["Tipos de sensor"], schemas.TipoSensorCreate, schemas.TipoSensorRead, TipoSensorRepository, "id_tipo_sensor"),
    ("/unidades-medida", ["Unidades de medida"], schemas.UnidadMedidaCreate, schemas.UnidadMedidaRead, UnidadMedidaRepository, "id_unidad"),
    ("/tipos-umbral", ["Tipos de umbral"], schemas.TipoUmbralCreate, schemas.TipoUmbralRead, TipoUmbralRepository, "id_tipo_umbral"),
    ("/dispositivos", ["Dispositivos"], schemas.DispositivoCreate, schemas.DispositivoRead, DispositivoRepository, "id_dispositivo"),
    ("/sensores", ["Sensores"], schemas.SensorCreate, schemas.SensorRead, SensorRepository, "id_sensor"),
    ("/componentes", ["Componentes eléctricos"], schemas.ComponenteElectricoCreate, schemas.ComponenteElectricoRead, ComponenteElectricoRepository, "id_componente"),
    ("/mediciones", ["Mediciones"], schemas.MedicionCreate, schemas.MedicionRead, MedicionRepository, "id_medicion"),
    ("/umbrales", ["Umbrales de alerta"], schemas.UmbralAlertaCreate, schemas.UmbralAlertaRead, UmbralAlertaRepository, "id_umbral"),
    ("/alertas", ["Alertas"], schemas.AlertaCreate, schemas.AlertaRead, AlertaRepository, "id_alerta"),
    ("/reportes", ["Reportes"], schemas.ReporteCreate, schemas.ReporteRead, ReporteRepository, "id_reporte"),
]

for prefix, tags, create_schema, read_schema, repo_cls, pk_name in RUTAS:
    crud = CRUDRouter(
        prefix=prefix,
        tags=tags,
        create_schema=create_schema,
        read_schema=read_schema,
        repository_cls=repo_cls,
        pk_name=pk_name,
    )
    app.include_router(crud.router)

app.include_router(reporte_detalle_router)


@app.get("/", tags=["Estado"])
def estado():
    return {"mensaje": "API Taller 1 - Medición de potencia con ACS712", "estado": "activo"}
