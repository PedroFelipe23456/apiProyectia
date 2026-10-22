"""
CRUDRouter: clase que, dado un modelo ORM, sus esquemas Pydantic y su
repositorio, genera automáticamente las 5 rutas REST estándar
(listar, obtener, crear, actualizar, eliminar). Cada entidad del
taller instancia esta clase una vez en app/modules/catalogos/router.py en lugar de
reescribir las mismas 5 rutas 14 veces (composición + genéricos).
"""
from typing import Type, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db


class CRUDRouter:
    def __init__(
        self,
        prefix: str,
        tags: List[str],
        create_schema: Type[BaseModel],
        read_schema: Type[BaseModel],
        repository_cls,
        pk_name: str,
        pk_type: type = int,
    ):
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.create_schema = create_schema
        self.read_schema = read_schema
        self.repository_cls = repository_cls
        self.pk_name = pk_name
        self.pk_type = pk_type
        self._registrar_rutas()

    def _registrar_rutas(self):
        read_schema = self.read_schema
        create_schema = self.create_schema
        repository_cls = self.repository_cls
        pk_name = self.pk_name
        pk_type = self.pk_type

        @self.router.get("/", response_model=List[read_schema])
        def listar(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
            repo = repository_cls(db)
            return repo.get_all(skip, limit)

        @self.router.get("/{item_id}", response_model=read_schema)
        def obtener(item_id: pk_type, db: Session = Depends(get_db)):
            repo = repository_cls(db)
            obj = repo.get_by_id(item_id, pk_name)
            if not obj:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            return obj

        @self.router.post("/", response_model=read_schema, status_code=201)
        def crear(item: create_schema, db: Session = Depends(get_db)):
            repo = repository_cls(db)
            return repo.create(item.model_dump())

        @self.router.put("/{item_id}", response_model=read_schema)
        def actualizar(item_id: pk_type, item: create_schema, db: Session = Depends(get_db)):
            repo = repository_cls(db)
            db_obj = repo.get_by_id(item_id, pk_name)
            if not db_obj:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            return repo.update(db_obj, item.model_dump(exclude_unset=True))

        @self.router.delete("/{item_id}", status_code=204)
        def eliminar(item_id: pk_type, db: Session = Depends(get_db)):
            repo = repository_cls(db)
            db_obj = repo.get_by_id(item_id, pk_name)
            if not db_obj:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            repo.delete(db_obj)
