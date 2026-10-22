import os
import json
import requests
from fastapi import APIRouter, Form, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.core.database import get_db
from app.db import repository as repo

load_dotenv()

router = APIRouter(tags=["WhatsApp"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SEVERIDADES = ["baja", "media", "alta", "critica"]
ESTADOS_ALERTA = ["nueva", "revisada", "resuelta"]
TIPOS_REPORTE = ["general", "alertas", "por_ubicacion", "por_componente", "consumo"]
TABLAS_VALIDAS = [
    "roles", "usuarios", "ubicaciones", "dispositivos", "sensores",
    "tipo_sensor", "unidades", "tipo_umbral", "componentes",
    "umbrales", "alertas", "reportes", "medicion", "ayuda", "desconocido",
]


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db),
):
    respuesta_texto = procesar_mensaje(Body, db)
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Message>{respuesta_texto}</Message></Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


# =====================================================================
# INTÉRPRETE DE INTENCIÓN (Ollama)
# =====================================================================
def obtener_nombres_componentes(db: Session):
    items = repo.ComponenteElectricoRepository(db).get_all(limit=100)
    return [c.nombre for c in items]


def interpretar_intencion(texto: str, nombres_componentes: list) -> dict:
    prompt = f"""Eres un clasificador de intenciones para un chatbot de WhatsApp que consulta una base de datos de monitoreo eléctrico de un parque.

Responde SOLO con un JSON válido, sin texto adicional, sin explicaciones, sin markdown. Formato exacto:
{{
  "tabla": uno de {TABLAS_VALIDAS},
  "componente": nombre EXACTO de esta lista si el usuario lo menciona, o null -> {nombres_componentes},
  "severidad": uno de {SEVERIDADES} o null,
  "estado": uno de {ESTADOS_ALERTA} o null,
  "tipo_reporte": uno de {TIPOS_REPORTE} o null,
  "orden": "asc" si pide el primero/más antiguo, "desc" si pide el último/más reciente (por defecto "desc"),
  "ver_todas": true si pide todas/todos/historial/lista, false si pide un solo dato (por defecto false)
}}

Mensaje del usuario: "{texto}"

JSON:"""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["response"])
        return data
    except Exception:
        return {"tabla": "desconocido"}


# =====================================================================
# ENRUTADOR PRINCIPAL
# =====================================================================
def procesar_mensaje(texto: str, db: Session) -> str:
    if texto.lower().strip() in ("ayuda", "menu", "menú"):
        return mostrar_ayuda()

    nombres = obtener_nombres_componentes(db)
    intencion = interpretar_intencion(texto, nombres)

    tabla = intencion.get("tabla", "desconocido")
    componente_nombre = intencion.get("componente")
    severidad = intencion.get("severidad")
    estado = intencion.get("estado")
    tipo_reporte = intencion.get("tipo_reporte")
    ascendente = intencion.get("orden") == "asc"
    ver_todas = bool(intencion.get("ver_todas"))

    componente = None
    if componente_nombre:
        componente = (
            db.query(repo.models.ComponenteElectrico)
            .filter(repo.models.ComponenteElectrico.nombre == componente_nombre)
            .first()
        )

    if tabla == "roles":
        return listar_roles(db)
    if tabla == "usuarios":
        return listar_usuarios(db)
    if tabla == "ubicaciones":
        return listar_ubicaciones(db)
    if tabla == "dispositivos":
        return listar_dispositivos(db)
    if tabla == "sensores":
        return listar_sensores(db)
    if tabla == "tipo_sensor":
        return listar_tipos_sensor(db)
    if tabla == "unidades":
        return listar_unidades(db)
    if tabla == "tipo_umbral":
        return listar_tipos_umbral(db)
    if tabla == "componentes":
        return listar_componentes(db)
    if tabla == "umbrales":
        return consultar_umbrales(db, componente)
    if tabla == "alertas":
        return consultar_alertas(db, severidad, estado, componente, ascendente, ver_todas)
    if tabla == "reportes":
        return consultar_reportes(db, tipo_reporte, ascendente, ver_todas)
    if tabla == "medicion":
        if componente:
            return medicion_de_componente(componente, db)
        return consultar_mediciones(db, ascendente, ver_todas)
    if tabla == "ayuda":
        return mostrar_ayuda()

    return (
        "No logré identificar qué necesitas 🤔\n"
        "Escribe *ayuda* para ver ejemplos de lo que puedo consultar."
    )


def mostrar_ayuda() -> str:
    return (
        "📋 *Puedes preguntarme cosas como:*\n"
        "- '¿qué usuarios hay?'\n"
        "- '¿cuáles son las ubicaciones?'\n"
        "- '¿cuánto consume la bomba de riego?'\n"
        "- 'dame las últimas alertas críticas'\n"
        "- 'muéstrame el primer reporte'\n"
        "- 'historial de mediciones'\n"
        "No necesitas usar palabras exactas, solo pregunta con tus palabras."
    )


# =====================================================================
# CATÁLOGOS
# =====================================================================
def listar_roles(db: Session) -> str:
    items = repo.RolRepository(db).get_all(limit=10)
    if not items:
        return "No hay roles registrados."
    lineas = [f"{r.id_rol}. {r.nombre_rol} — {r.descripcion or 'sin descripción'}" for r in items]
    return "👤 *Roles:*\n" + "\n".join(lineas)


def listar_usuarios(db: Session) -> str:
    items = repo.UsuarioRepository(db).get_all(limit=10)
    if not items:
        return "No hay usuarios registrados."
    lineas = [f"{u.id_usuario}. {u.nombre} ({u.email})" for u in items]
    return "👥 *Usuarios:*\n" + "\n".join(lineas)


def listar_ubicaciones(db: Session) -> str:
    items = repo.UbicacionRepository(db).get_all(limit=10)
    if not items:
        return "No hay ubicaciones registradas."
    lineas = [f"{u.id_ubicacion}. {u.nombre} — {u.descripcion or ''}" for u in items]
    return "📍 *Ubicaciones:*\n" + "\n".join(lineas)


def listar_tipos_sensor(db: Session) -> str:
    items = repo.TipoSensorRepository(db).get_all(limit=10)
    if not items:
        return "No hay tipos de sensor registrados."
    lineas = [f"{s.id_tipo_sensor}. {s.modelo} ({s.tipo_magnitud}) rango {s.rango_min}-{s.rango_max}" for s in items]
    return "🔧 *Tipos de sensor:*\n" + "\n".join(lineas)


def listar_unidades(db: Session) -> str:
    items = repo.UnidadMedidaRepository(db).get_all(limit=10)
    if not items:
        return "No hay unidades de medida registradas."
    lineas = [f"{u.id_unidad}. {u.nombre} ({u.simbolo})" for u in items]
    return "📏 *Unidades de medida:*\n" + "\n".join(lineas)


def listar_tipos_umbral(db: Session) -> str:
    items = repo.TipoUmbralRepository(db).get_all(limit=10)
    if not items:
        return "No hay tipos de umbral registrados."
    lineas = [f"{t.id_tipo_umbral}. {t.nombre} — {t.descripcion or ''}" for t in items]
    return "⚠️ *Tipos de umbral:*\n" + "\n".join(lineas)


def listar_dispositivos(db: Session) -> str:
    items = repo.DispositivoRepository(db).get_all(limit=10)
    if not items:
        return "No hay dispositivos registrados."
    lineas = [f"{d.nombre} — {d.estado} — {d.ubicacion.nombre if d.ubicacion else '?'}" for d in items]
    return "📡 *Dispositivos:*\n" + "\n".join(lineas)


def listar_sensores(db: Session) -> str:
    items = repo.SensorRepository(db).get_all(limit=10)
    if not items:
        return "No hay sensores registrados."
    lineas = []
    for s in items:
        tipo = s.tipo_sensor.modelo if s.tipo_sensor else "?"
        disp = s.dispositivo.nombre if s.dispositivo else "?"
        lineas.append(f"{s.numero_serie} — {tipo} en {disp}")
    return "🔌 *Sensores:*\n" + "\n".join(lineas)


def listar_componentes(db: Session) -> str:
    items = repo.ComponenteElectricoRepository(db).get_all(limit=10)
    if not items:
        return "No hay componentes registrados."
    lineas = [f"{c.nombre} ({c.tipo_componente}) — {c.voltaje_nominal_v}V / {c.potencia_nominal_w}W" for c in items]
    return "🔋 *Componentes eléctricos:*\n" + "\n".join(lineas)


# =====================================================================
# TABLAS "VIVAS"
# =====================================================================
def consultar_umbrales(db: Session, componente) -> str:
    query = db.query(repo.models.UmbralAlerta)
    if componente:
        query = query.filter(repo.models.UmbralAlerta.id_componente == componente.id_componente)
    items = query.limit(10).all()
    if not items:
        return "No hay umbrales registrados para esa consulta."
    lineas = []
    for u in items:
        comp = u.componente.nombre if u.componente else "?"
        tipo = u.tipo_umbral.nombre if u.tipo_umbral else "?"
        lineas.append(f"{comp} — {tipo}: {u.valor_limite}")
    titulo = f"🚨 *Umbrales de {componente.nombre}:*\n" if componente else "🚨 *Umbrales de alerta:*\n"
    return titulo + "\n".join(lineas)


def consultar_alertas(db: Session, severidad, estado, componente, ascendente: bool, ver_todas: bool) -> str:
    query = db.query(repo.models.Alerta)
    if severidad:
        query = query.filter(repo.models.Alerta.nivel_severidad == severidad)
    if estado:
        query = query.filter(repo.models.Alerta.estado == estado)
    if componente:
        query = query.join(repo.models.Medicion).filter(
            repo.models.Medicion.id_componente == componente.id_componente
        )

    orden = repo.models.Alerta.fecha_hora.asc() if ascendente else repo.models.Alerta.fecha_hora.desc()
    query = query.order_by(orden)
    items = query.limit(10 if ver_todas else 1).all()

    if not items:
        return "No encontré alertas con esos criterios."

    lineas = [f"[{a.nivel_severidad.upper()}] {a.mensaje} ({a.estado}) — {a.fecha_hora.strftime('%d/%m %H:%M')}" for a in items]
    if ver_todas:
        titulo = "🔔 *Alertas:*\n"
    elif ascendente:
        titulo = "🔔 *Primera alerta registrada:*\n"
    else:
        titulo = "🔔 *Última alerta:*\n"
    return titulo + "\n".join(lineas)


def consultar_reportes(db: Session, tipo_reporte, ascendente: bool, ver_todas: bool) -> str:
    query = db.query(repo.models.Reporte)
    if tipo_reporte:
        query = query.filter(repo.models.Reporte.tipo_reporte == tipo_reporte)

    orden = repo.models.Reporte.fecha_generacion.asc() if ascendente else repo.models.Reporte.fecha_generacion.desc()
    query = query.order_by(orden)
    items = query.limit(10 if ver_todas else 1).all()

    if not items:
        return "No encontré reportes con esos criterios."

    lineas = []
    for r in items:
        usuario_nombre = r.usuario.nombre if r.usuario else "?"
        lineas.append(f"{r.tipo_reporte} — {usuario_nombre} ({r.fecha_inicio} a {r.fecha_fin})")

    if ver_todas:
        titulo = "📄 *Reportes:*\n"
    elif ascendente:
        titulo = "📄 *Primer reporte registrado:*\n"
    else:
        titulo = "📄 *Último reporte:*\n"
    return titulo + "\n".join(lineas)


def consultar_mediciones(db: Session, ascendente: bool, ver_todas: bool) -> str:
    orden = repo.models.Medicion.fecha_hora.asc() if ascendente else repo.models.Medicion.fecha_hora.desc()
    query = db.query(repo.models.Medicion).order_by(orden)
    items = query.limit(10 if ver_todas else 1).all()
    if not items:
        return "No hay mediciones registradas."
    lineas = []
    for m in items:
        nombre = m.componente.nombre if m.componente else "?"
        lineas.append(f"{nombre} — {m.potencia_w}W, {m.voltaje_v}V, {m.corriente_a}A")

    if ver_todas:
        titulo = "📊 *Mediciones:*\n"
    elif ascendente:
        titulo = "📊 *Primera medición registrada:*\n"
    else:
        titulo = "📊 *Última medición:*\n"
    return titulo + "\n".join(lineas)


def medicion_de_componente(componente, db: Session) -> str:
    medicion_repo = repo.MedicionRepository(db)
    ultimas = medicion_repo.get_by_componente(componente.id_componente, limit=1)
    if not ultimas:
        return f"'{componente.nombre}' no tiene mediciones registradas todavía."
    m = ultimas[0]
    return (
        f"📊 {componente.nombre}\n"
        f"Corriente: {m.corriente_a} A\n"
        f"Voltaje: {m.voltaje_v} V\n"
        f"Potencia: {m.potencia_w} W\n"
        f"Energía: {m.energia_kwh} kWh\n"
        f"Fecha: {m.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
    )