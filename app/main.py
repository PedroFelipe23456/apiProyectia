"""
API Taller 1 - Monitoreo de potencia (ESP32 + ACS712), control de motor DC y visión YOLOv8.

Punto de entrada: crea la app y registra cada módulo.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.modules.catalogos.router import crear_routers as routers_catalogos
from app.modules.energia.router import router as energia_router
from app.modules.motor.router import router as motor_router
from app.modules.teclado.router import router as teclado_router
from app.modules.vision.router import router as vision_router
from app.modules.whatsapp.router import router as whatsapp_router

# 1. Importación del router de Telegram
from app.telegram_router import router as telegram_router

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
app.include_router(teclado_router)
for r in routers_catalogos():
    app.include_router(r)
app.include_router(vision_router)
app.include_router(whatsapp_router)

# 2. Registro de la ruta de Telegram
app.include_router(telegram_router)


# ---------------- Aplicación web ----------------
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
INDEX_HTML = os.path.join(STATIC_PATH, "index.html")

class StaticSinCache(StaticFiles):
    """Obliga al navegador a revalidar (ETag) los archivos de la web en cada carga."""

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


app.mount("/static", StaticSinCache(directory=STATIC_PATH), name="static")


SIN_CACHE = {"Cache-Control": "no-cache"}


@app.get("/", include_in_schema=False)
def aplicacion_web():
    return FileResponse(INDEX_HTML, headers=SIN_CACHE)


@app.get("/app", include_in_schema=False)
def aplicacion_web_alias():
    """Ruta anterior de la app móvil; se mantiene para no romper enlaces."""
    return FileResponse(INDEX_HTML, headers=SIN_CACHE)


@app.get("/salud", tags=["Estado"])
def salud():
    return {"mensaje": "API Taller - PowerMonitor IoT", "estado": "activo"}