"""
API Taller 1 - Monitoreo de potencia (ESP32 + ACS712), control de motor DC y visión YOLOv8.

Punto de entrada: crea la app y registra cada módulo.

    app/
      core/      conexión a la base de datos y CRUD genérico
      db/        modelos ORM, esquemas Pydantic y repositorios
      modules/
        energia/    mediciones de voltaje, corriente y potencia
        motor/      control del motor DC desde la web
        catalogos/  CRUD de roles, usuarios, sensores, umbrales, reportes...
        vision/     detección con YOLOv8
        whatsapp/   chatbot de consultas (Twilio + Ollama)
      static/    aplicación web (dashboard de energía + control de motor)
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.modules.catalogos.router import crear_routers as routers_catalogos
from app.modules.energia.router import router as energia_router
from app.modules.motor.router import router as motor_router
from app.modules.vision.router import router as vision_router
from app.modules.whatsapp.router import router as whatsapp_router

app = FastAPI(
    title="API Taller 1 - PowerMonitor IoT",
    description="Monitoreo de potencia eléctrica, control de motor DC y visión artificial.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(energia_router)
app.include_router(motor_router)
for r in routers_catalogos():
    app.include_router(r)
app.include_router(vision_router)
app.include_router(whatsapp_router)


# ---------------- Aplicación web ----------------
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
INDEX_HTML = os.path.join(STATIC_PATH, "index.html")

app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


@app.get("/", include_in_schema=False)
def aplicacion_web():
    return FileResponse(INDEX_HTML)


@app.get("/app", include_in_schema=False)
def aplicacion_web_alias():
    """Ruta anterior de la app móvil; se mantiene para no romper enlaces."""
    return FileResponse(INDEX_HTML)


@app.get("/salud", tags=["Estado"])
def salud():
    return {"mensaje": "API Taller - PowerMonitor IoT", "estado": "activo"}
