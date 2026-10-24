import json
import requests
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

# Importar repositorio de mediciones de forma segura
try:
    from app.db.repository import MedicionRepository
except ImportError:
    try:
        from app.repository import MedicionRepository
    except ImportError:
        MedicionRepository = None

router = APIRouter(prefix="/telegram", tags=["Bot Telegram LLM"])

TELEGRAM_TOKEN = "8928340214:AAH14fIWbDkTPg15VdscJECwDkquil0Qr2g"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_LLM = "qwen2.5:1.5b-instruct"

ESTADO_LED = False


def procesar_intencion_con_llm(mensaje: str) -> dict:
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
        # Se incrementa el timeout a 12s para permitir la inferencia de Ollama en local
        res = requests.post(OLLAMA_URL, json=payload, timeout=12)
        if res.status_code == 200:
            datos = json.loads(res.json().get("response", "{}"))
            return datos
    except Exception as e:
        print(f"⚠️ Ollama local no respondió, aplicando reglas rápidas: {e}")

    # Respaldo por reglas rápidas en caso de fallo o timeout
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
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "mensaje": "Body invalido"}

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        texto_usuario = data["message"]["text"]

        analisis = procesar_intencion_con_llm(texto_usuario)
        intencion = analisis.get("intencion", "desconocida")

        respuesta_texto = ""

        if intencion == "encender_led":
            ESTADO_LED = True
            respuesta_texto = "💡 ¡Entendido! He encendido el LED del ESP32."

        elif intencion == "apagar_led":
            ESTADO_LED = False
            respuesta_texto = "🌑 Entendido. He apagado el LED del ESP32."

        elif intencion in ["obtener_sensor_actual", "obtener_ultimo_registro"]:
            if MedicionRepository is not None:
                try:
                    repo = MedicionRepository(db)
                    mediciones = repo.get_all(limit=1)
                    if mediciones:
                        m = mediciones[0]
                        if intencion == "obtener_sensor_actual":
                            respuesta_texto = (
                                f"⚡ *Lectura Actual del Sensor (ACS712):*\n\n"
                                f"• *Voltaje:* {getattr(m, 'voltaje_v', 'N/A')} V\n"
                                f"• *Corriente:* {getattr(m, 'corriente_a', 'N/A')} A\n"
                                f"• *Potencia:* {getattr(m, 'potencia_w', 'N/A')} W\n"
                                f"• *Fecha:* {getattr(m, 'fecha_hora', 'N/A')}"
                            )
                        else:
                            respuesta_texto = (
                                f"📋 *Último Registro Guardado:* ID #{getattr(m, 'id_medicion', '1')} | "
                                f"Potencia: {getattr(m, 'potencia_w', '0')} W"
                            )
                    else:
                        respuesta_texto = "⚠️ No hay registros de mediciones en la base de datos."
                except Exception as db_err:
                    print(f"Error consultando la BD: {db_err}")
                    respuesta_texto = "⚡ *Lectura Sensor (Simulada):* 120.5 V | 0.45 A | 54.2 W"
            else:
                respuesta_texto = "⚡ *Lectura Sensor (Simulada):* 120.0 V | 0.50 A | 60.0 W"

        elif intencion == "saludo":
            estado_str = "ENCENDIDO 💡" if ESTADO_LED else "APAGADO 🌑"
            respuesta_texto = (
                f"👋 ¡Hola! Soy el asistente IoT de PowerMonitor.\n\n"
                f"Estado actual del LED: *{estado_str}*\n\n"
                f"Prueba diciéndome:\n"
                f"- _'Prende la luz'_\n"
                f"- _'¿Cuál es el valor del sensor?'_\n"
                f"- _'Apaga el led'_"
            )
        else:
            respuesta_texto = "🤖 Disculpa, no comprendí esa orden. Intenta pidiéndome encender el LED o consultar el sensor."

        try:
            requests.post(TELEGRAM_URL, json={
                "chat_id": chat_id,
                "text": respuesta_texto,
                "parse_mode": "Markdown"
            })
        except Exception as tel_err:
            print(f"Error enviando mensaje a Telegram: {tel_err}")

    return {"status": "ok"}


@router.get("/estado-led")
def consultar_estado_led():
    global ESTADO_LED
    return {"led_encendido": ESTADO_LED}