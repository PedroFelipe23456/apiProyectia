"""
Módulo Catálogos: CRUD de las tablas de configuración del sistema
(roles, usuarios, ubicaciones, sensores, componentes, umbrales, alertas, reportes).

Cada tabla usa el CRUDRouter genérico, que arma las 5 rutas REST
(listar, obtener, crear, actualizar, eliminar).
Las mediciones NO están aquí: tienen su propio módulo (energia).
"""
from typing import List

from fastapi import APIRouter

from app.core.crud_router import CRUDRouter
from app.db import schemas
from app.db.repository import (
    RolRepository,
    UsuarioRepository,
    UbicacionRepository,
    TipoSensorRepository,
    UnidadMedidaRepository,
    TipoUmbralRepository,
    DispositivoRepository,
    SensorRepository,
    ComponenteElectricoRepository,
    UmbralAlertaRepository,
    AlertaRepository,
    ReporteRepository,
)
from app.modules.catalogos.reporte_detalle import router as reporte_detalle_router

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
    ("/umbrales", ["Umbrales de alerta"], schemas.UmbralAlertaCreate, schemas.UmbralAlertaRead, UmbralAlertaRepository, "id_umbral"),
    ("/alertas", ["Alertas"], schemas.AlertaCreate, schemas.AlertaRead, AlertaRepository, "id_alerta"),
    ("/reportes", ["Reportes"], schemas.ReporteCreate, schemas.ReporteRead, ReporteRepository, "id_reporte"),
]


def crear_routers() -> List[APIRouter]:
    """Devuelve todos los routers del módulo para registrarlos en main.py."""
    routers = [
        CRUDRouter(
            prefix=prefix,
            tags=tags,
            create_schema=create_schema,
            read_schema=read_schema,
            repository_cls=repo_cls,
            pk_name=pk_name,
        ).router
        for prefix, tags, create_schema, read_schema, repo_cls, pk_name in RUTAS
    ]
    routers.append(reporte_detalle_router)
    return routers
