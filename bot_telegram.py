"""
bot_telegram.py - Bot de Telegram (long polling) para PowerMonitor IoT.

Corre en TU PC (no en Render): pregunta a Telegram si hay mensajes nuevos, le pregunta a
Ollama (LLM local) qué quiso decir el usuario y ejecuta la acción llamando a la API de Render.

    Telegram <--> bot_telegram.py <--> Ollama (intención)
                        |--> API Render: /mediciones/..., /motor/ (control real del motor)

Variables (.env): TELEGRAM_TOKEN, API_BASE (opcional), OLLAMA_URL (opcional), OLLAMA_MODEL (opcional)
"""
import json
import os
import re
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TG = f"https://api.telegram.org/bot{TOKEN}"
API = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODELO = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct")

estado_led = False

INTENCIONES = ["encender_led", "apagar_led", "leer_sensor", "ultimo_registro", "resumen",
               "motor_adelante", "motor_atras", "motor_stop", "estado_motor", "ayuda", "desconocido"]

PROMPT = """Eres el clasificador de intenciones de un bot de Telegram de un sistema IoT de potencia
(ESP32 + sensor ACS712 + motor DC). Lee el mensaje (español, cualquier forma de hablar) y responde SOLO
un JSON: {"intent": "<intencion>", "velocidad": <0-100 o null>}.
Intenciones:
- encender_led / apagar_led: prender o apagar la luz o el LED.
- leer_sensor: lectura ACTUAL de voltaje, corriente o potencia.
- ultimo_registro: el último registro guardado en la base de datos.
- resumen: promedio, máximo, mínimo o estadísticas de la potencia, energía total.
- motor_adelante / motor_atras / motor_stop: mover el motor hacia adelante, atrás, o detenerlo.
  "velocidad" es el porcentaje si el usuario lo dice (si no, null).
- estado_motor: cómo está el motor / si el ESP32 está conectado.
- ayuda: saludo o qué puedes hacer.
- desconocido: cualquier otra cosa."""


# ---------------- 1. Intención ----------------
def intencion_llm(texto):
    r = requests.post(f"{OLLAMA}/api/chat", timeout=25, json={
        "model": MODELO, "stream": False, "format": "json", "options": {"temperature": 0},
        "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": texto}]})
    r.raise_for_status()
    d = json.loads(r.json()["message"]["content"])
    if d.get("intent") not in INTENCIONES:
        raise ValueError("intención inválida")
    return d["intent"], d.get("velocidad")


def intencion_reglas(texto):
    t = texto.lower()
    num = re.search(r"(\d{1,3})\s*%?", t)
    vel = min(int(num.group(1)), 100) if num else None
    if re.search(r"ap[aá]g|desactiv|quita", t) and re.search(r"led|luz|foco", t): return "apagar_led", None
    if re.search(r"enciend|prend|activ|pon", t) and re.search(r"led|luz|foco", t): return "encender_led", None
    if re.search(r"det[eé]n|para |parar|stop|frena|alto", t + " "): return "motor_stop", None
    if re.search(r"atr[aá]s|reversa|retroced", t): return "motor_atras", vel
    if re.search(r"adelante|avanza|mueve|gira|arranca|motor", t) and not re.search(r"estado|conectad|c[oó]mo", t):
        return "motor_adelante", vel
    if re.search(r"estado|conectad|c[oó]mo est", t): return "estado_motor", None
    if re.search(r"promedio|m[aá]xim|m[ií]nim|resumen|estad[ií]stic|total|energ", t): return "resumen", None
    if re.search(r"[uú]ltimo|registro|historial", t): return "ultimo_registro", None
    if re.search(r"sensor|voltaje|corriente|potencia|mide|lectura|watt", t): return "leer_sensor", None
    if re.search(r"hola|buen|ayuda|qu[eé] puedes|/start|/help", t): return "ayuda", None
    return "desconocido", None


def detectar(texto):
    # Órdenes críticas (LED y parar motor): las decide el código fijo, no el LLM,
    # porque un modelo pequeño confunde "apaga" con "enciende".
    r = intencion_reglas(texto)
    if r[0] in ("encender_led", "apagar_led", "motor_stop"):
        return r + ("reglas",)
    try:
        return intencion_llm(texto) + ("LLM",)
    except Exception as e:
        print("  (Ollama no disponible, uso reglas:", type(e).__name__, ")")
        return intencion_reglas(texto) + ("reglas",)


# ---------------- 2. Acciones ----------------
def get(ruta, **p):
    r = requests.get(API + ruta, params=p, timeout=60)
    r.raise_for_status()
    return r.json()


def ejecutar(intent, vel):
    global estado_led
    if intent in ("encender_led", "apagar_led"):
        encender = intent == "encender_led"
        r = requests.post(API + "/telegram/estado-led", json={"encendido": encender}, timeout=60)
        r.raise_for_status()
        estado_led = encender
        return ("💡 Listo, LED encendido. El ESP32 lo aplica en ~2 s." if encender
                else "🌑 Listo, LED apagado. El ESP32 lo aplica en ~2 s.")
    if intent in ("leer_sensor", "ultimo_registro"):
        datos = get("/mediciones/", limit=1)
        if not datos:
            return "⚠️ Todavía no hay mediciones guardadas."
        m = datos[0]
        if intent == "leer_sensor":
            return (f"⚡ Última lectura del sensor ACS712\n• Voltaje: {m['voltaje_v']} V\n"
                    f"• Corriente: {m['corriente_a']} A\n• Potencia: {m['potencia_w']} W\n• Fecha: {m['fecha_hora']}")
        return f"📋 Último registro #{m['id_medicion']}: {m['potencia_w']} W ({m['fecha_hora']})"
    if intent == "resumen":
        r = get("/mediciones/resumen")
        return (f"📊 Resumen de {r['total']} mediciones\n• Potencia promedio: {r['potencia_promedio_w']} W\n"
                f"• Máxima: {r['potencia_max_w']} W\n• Mínima: {r['potencia_min_w']} W\n"
                f"• Energía total: {r['energia_total_kwh']} kWh")
    if intent in ("motor_adelante", "motor_atras", "motor_stop"):
        direccion = {"motor_adelante": "adelante", "motor_atras": "atras", "motor_stop": "stop"}[intent]
        v = 0 if direccion == "stop" else int(vel if vel is not None else 60)
        r = requests.put(API + "/motor/", json={"velocidad": max(0, min(100, v)), "direccion": direccion}, timeout=60)
        r.raise_for_status()
        return "🛑 Motor detenido." if direccion == "stop" else f"⚙️ Motor {direccion} al {v}%."
    if intent == "estado_motor":
        e = get("/motor/estado")
        con = "conectado ✅" if e["conectado"] else "desconectado ❌"
        return f"🔌 ESP32 {con}\n• Motor: {e['direccion']} al {e['velocidad']}%"
    if intent == "ayuda":
        return ("👋 Hola, soy el asistente de PowerMonitor IoT. Háblame normal:\n"
                "• «prende la luz» / «apaga el led»\n• «¿cuánto está midiendo el sensor?»\n"
                "• «dame el último registro»\n• «dame el resumen de potencia»\n"
                "• «mueve el motor adelante al 70%» / «detén el motor»\n• «¿está conectado el ESP32?»")
    return "🤖 No entendí. Escribe «ayuda» para ver lo que puedo hacer."


# ---------------- 3. Bucle de Telegram ----------------
def enviar(chat, texto):
    requests.post(f"{TG}/sendMessage", json={"chat_id": chat, "text": texto}, timeout=30)


def main():
    if not TOKEN:
        raise SystemExit("Falta TELEGRAM_TOKEN en el .env")
    requests.get(f"{TG}/deleteWebhook", timeout=30)   # polling y webhook no pueden convivir
    print("Bot v2 (LED vía API) listo. API:", API, "| Escríbele en Telegram. Ctrl+C para salir.")
    offset = None
    while True:
        try:
            r = requests.get(f"{TG}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=40).json()
        except requests.RequestException as e:
            print("Error de red:", e); time.sleep(3); continue
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            texto, chat = msg.get("text"), msg.get("chat", {}).get("id")
            if not texto or not chat:
                continue
            intent, vel, motor = detectar(texto)
            print(f"[{chat}] {texto!r} -> {intent} (vel={vel}) vía {motor}")
            try:
                enviar(chat, ejecutar(intent, vel))
            except Exception as e:
                print("  error:", e)
                enviar(chat, "⚠️ La API no respondió (si estaba dormida, intenta otra vez en 30 s).")


if __name__ == "__main__":
    main()
