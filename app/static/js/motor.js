// Módulo Motor: slider con debounce, dirección, DETENER y estado del ESP32.
import { enviarJSON, fmt, toast } from "./api.js";

const $ = (id) => document.getElementById(id);
const estado = { velocidad: 0, direccion: "stop" };
let temporizador = null;
let arrastrando = false;
let sincronizado = false;

const TEXTO_DIR = { adelante: "adelante", atras: "atrás", stop: "detenido" };

function pintar() {
  $("motor-valor").textContent = estado.velocidad + "%";
  $("motor-adelante").setAttribute("aria-pressed", String(estado.direccion === "adelante"));
  $("motor-atras").setAttribute("aria-pressed", String(estado.direccion === "atras"));
  $("motor-actual").textContent = estado.direccion === "stop"
    ? "Motor: detenido"
    : `Motor: ${TEXTO_DIR[estado.direccion]} al ${estado.velocidad}%`;
}

async function enviar() {
  try {
    const r = await enviarJSON("/motor/", "PUT", estado);
    Object.assign(estado, r);
    pintar();
  } catch (e) {
    toast("No se pudo enviar la orden al motor (" + e.message + ").");
  }
}

export function initMotor() {
  const slider = $("motor-velocidad");
  // El número cambia al instante; el PUT sale 300 ms después del último movimiento.
  slider.addEventListener("input", () => {
    estado.velocidad = Number(slider.value);
    pintar();
    clearTimeout(temporizador);
    temporizador = setTimeout(enviar, 300);
  });
  slider.addEventListener("pointerdown", () => { arrastrando = true; });
  window.addEventListener("pointerup", () => { arrastrando = false; });

  $("motor-adelante").addEventListener("click", () => { estado.direccion = "adelante"; pintar(); enviar(); });
  $("motor-atras").addEventListener("click", () => { estado.direccion = "atras"; pintar(); enviar(); });
  // DETENER sale de inmediato. Conserva la velocidad para volver a arrancar con ella.
  $("motor-stop").addEventListener("click", () => {
    clearTimeout(temporizador);
    estado.direccion = "stop";
    pintar();
    enviar();
  });
  pintar();
}

/** Lo llama app.js cada vez que llega /motor/estado. */
export function actualizarEstado(r) {
  if (!sincronizado) {
    estado.velocidad = r.velocidad;
    estado.direccion = r.direccion;
    $("motor-velocidad").value = r.velocidad;
    sincronizado = true;
    pintar();
  }
  const pill = $("motor-conexion");
  pill.classList.toggle("on", r.conectado);
  pill.classList.toggle("off", !r.conectado);
  $("motor-conexion-texto").textContent = r.conectado ? "ESP32 conectado" : "ESP32 desconectado";
  $("motor-conexion-detalle").textContent = r.segundos_desde_contacto === null
    ? "El ESP32 aún no se ha comunicado desde que arrancó el servidor."
    : `Último contacto hace ${fmt(r.segundos_desde_contacto, 1)} s`;

  const l = r.lectura;
  $("vivo-v").textContent = l ? fmt(l.voltaje_v, 1) : "--";
  $("vivo-i").textContent = l ? fmt(l.corriente_ma, 0) : "--";
  $("vivo-p").textContent = l ? fmt(l.potencia_w, 2) : "--";
}

export function estaArrastrando() {
  return arrastrando;
}
