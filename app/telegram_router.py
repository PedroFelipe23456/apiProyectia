import json
import os
import requests
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.repository import MedicionRepository

router = APIRouter(prefix="/telegram", tags=["Bot Telegram LLM"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")  # va en .env, nunca en el código
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Endpoint local de Ollama (Qwen2.5)
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_LLM = "qwen2.5:1.5b-instruct"

ESTADO_LED = False


def procesar_intencion_con_llm(mensaje: str) -> dict:
    """Envía la orden a Ollama para clasificar la intención en formato JSON."""
    prompt_sistema = f"""
    Eres el clasificador de intenciones para un sistema IoT de potencia (ESP32 + ACS712).
    Analiza el mensaje del usuario y clasifícalo EN UNA sola de estas intenciones:
    - "encender_led": si el usuario quiere encender, prender o iluminar la luz/LED.
    - "apagar_led": si el usuario quiere apagar la luz/LED.
    - "obtener_sensor_actual": si consulta lecturas actuales, voltaje, corriente o potencia.
    - "obtener_ultimo_registro": si pide el último registro guardado o historial.
    - "saludo": si saluda, da los buenos días o pregunta qué puede hacer.
    - "desconocida": para cualquier otra cosa fuera del tema.

    Responde ÚNICAMENTE con un JSON válido en este formato exacto:
    {{"intencion": "nombre_intencion"}}

    Mensaje: "{mensaje}"
    """

    try:
        payload = {
            "model": MODELO_LLM,
            "prompt": prompt_sistema,
            "stream": False,
            "format": "json"
        }
        res = requests.post(OLLAMA_URL, json=payload, timeout=6)
        if res.status_code == 200:
            datos = json.loads(res.json().get("response", "{}"))
            print(f"🤖 LLM ({MODELO_LLM}) identificó:", datos)
            return datos
    except Exception as e:
        print(f"⚠️ Ollama no respondió, usando respaldo por reglas: {e}")

    # Respaldo rápido por palabras clave
    msg = mensaje.lower().strip()
    if any(p in msg for p in ["enciende", "prende", "encender", "luz"]):
        return {"intencion": "encender_led"}
    elif any(p in msg for p in ["apaga", "apagar", "desconecta"]):
        return {"intencion": "apagar_led"}
    elif any(p in msg for p in ["valor", "lectura", "sensor", "potencia", "actual"]):
        return {"intencion": "obtener_sensor_actual"}
    elif any(p in msg for p in ["ultimo", "registro", "historial"]):
        return {"intencion": "obtener_ultimo_registro"}
    elif any(p in msg for p in ["/start", "hola", "buenas", "ayuda"]):
        return {"intencion": "saludo"}
    else:
        return {"intencion": "desconocida"}


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    global ESTADO_LED
    data = await request.json()
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        texto_usuario = data["message"]["text"]
        
        analisis = procesar_intencion_con_llm(texto_usuario)
        intencion = analisis.get("intencion", "desconocida")
        
        respuesta_texto = ""
        repo = MedicionRepository(db)
        
        if intencion == "encender_led":
            ESTADO_LED = True
            respuesta_texto = "💡 ¡Entendido! He encendido el LED del ESP32."
            
        elif intencion == "apagar_led":
            ESTADO_LED = False
            respuesta_texto = "🌑 Entendido. He apagado el LED del ESP32."
            
        elif intencion == "obtener_sensor_actual":
            mediciones = repo.get_all(limit=1)
            if mediciones:
                m = mediciones[0]
                respuesta_texto = (
                    f"⚡ *Lectura Actual del Sensor (ACS712):*\n\n"
                    f"• *Voltaje:* {m.voltaje_v} V\n"
                    f"• *Corriente:* {m.corriente_a} A\n"
                    f"• *Potencia:* {m.potencia_w} W\n"
                    f"• *Fecha:* {m.fecha_hora}"
                )
            else:
                respuesta_texto = "⚠️ No hay registros de mediciones en PostgreSQL."
                
        elif intencion == "obtener_ultimo_registro":
            mediciones = repo.get_all(limit=1)
            if mediciones:
                m = mediciones[0]
                respuesta_texto = f"📋 *Último Registro Guardado:* ID #{m.id_medicion} - Potencia: {m.potencia_w} W ({m.fecha_hora})"
            else:
                respuesta_texto = "⚠️ Sin registros en la base de datos."
                
        elif intencion == "saludo":
            estado_str = "ENCENDIDO 💡" if ESTADO_LED else "APAGADO 🌑"
            respuesta_texto = (
                f"👋 ¡Hola! Soy el asistente IoT impulsado por Qwen2.5 local.\n\n"
                f"Estado actual del LED: *{estado_str}*\n\n"
                f"Puedes hablarme de forma natural:\n"
                f"- _'Porfa prende la luz'_\n"
                f"- _'¿Cuánto está midiendo el sensor?'_\n"
                f"- _'Muéstrame el último dato'_\n"
                f"- _'Apaga el led'_"
            )
        else:
            respuesta_texto = (
                "🤖 Disculpa, no comprendí esa orden. "
                "Intenta preguntarme sobre las mediciones del sensor o pedirme encender/apagar el LED."
            )
            
        requests.post(TELEGRAM_URL, json={
            "chat_id": chat_id,
            "text": respuesta_texto,
            "parse_mode": "Markdown"
        })
        
    return {"status": "ok"}


@router.get("/estado-led")
def consultar_estado_led():
    global ESTADO_LED
    return {"led_encendido": ESTADO_LED}


class OrdenLed(BaseModel):
    encendido: bool


@router.post("/estado-led")
def fijar_estado_led(orden: OrdenLed):
    """Lo llama bot_telegram.py. El ESP32 lee el valor con GET /telegram/estado-led cada 2 s."""
    global ESTADO_LED
    ESTADO_LED = orden.encendido
    return {"led_encendido": ESTADO_LED}