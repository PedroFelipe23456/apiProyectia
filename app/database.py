"""
Configuración de la conexión a la base de datos.
Lee la cadena de conexión desde la variable de entorno DATABASE_URL
(ver .env.example). Debe apuntar a la misma base PostgreSQL en la nube
donde se ejecutó taller1_basedatos.sql (Parte 1 del taller).
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://usuario:password@host:5432/taller1_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
