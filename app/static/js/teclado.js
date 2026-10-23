// Módulo Teclado: el teclado HX-543 en la web. Cada tecla se envía a POST /teclado/,
// el ESP32 la recoge en su próxima consulta (GET /motor/) y la ejecuta en el LCD.
import { pedir, enviarJSON } from "./api.js";

const $ = (id) => document.getElementById(id);

// Mismo orden que el teclado físico (4 x 4) y mismas opciones que el sketch
const TECLAS = [
  ["1", "Valor actual"], ["2", "Último reg."], ["3", "Prom. 24 h"], ["A", "Guardar"],
  ["4", "Máx/mín 24 h"], ["5", "Prom. 1 h"], ["6", "Registros"], ["B", "Calibrar 0"],
  ["7", "Alerta"], ["8", "P. aparente"], ["9", "Desviación"], ["C", ""],
  ["*", ""], ["0", "LEDs"], ["#", ""], ["D", ""],
];

const AYUDA = {
  "1": "Voltaje y corriente medidos ahora",
  "2": "Último registro guardado en la base de datos",
  "3": "Potencia promedio de las últimas 24 h",
  "4": "Potencia máxima y mínima de las últimas 24 h",
  "5": "Potencia promedio de la última hora",
  "6": "Cantidad de registros de las últimas 24 h",
  "7": "¿La potencia supera 15 W?",
  "8": "Potencia aparente (VA)",
  "9": "Desviación estándar de la potencia (24 h)",
  "0": "Enciende / apaga los 3 LEDs",
  "A": "Guarda la medición actual en la base de datos",
  "B": "Recalibra el cero del ACS712 (motor y carga apagados)",
};

let esperando = null;   // id de la última tecla enviada que el ESP32 aún no ejecuta
let timer = null;

function pintarEnvio(clase, texto) {
  $("teclado-envio").className = "envio" + (clase ? " " + clase : "");
  $("teclado-envio-texto").textContent = texto;
}

async function pulsar(tecla, boton) {
  boton.classList.add("pulsada");
  setTimeout(() => boton.classList.remove("pulsada"), 150);
  if (navigator.vibrate) navigator.vibrate(15);
  try {
    const r = await enviarJSON("/teclado/", "POST", { tecla });
    $("lcd-1").textContent = r.linea1;
    $("lcd-2").textContent = r.linea2;
    esperando = r.id;
    pintarEnvio("pendiente", `Tecla ${tecla} enviada · esperando al ESP32`);
    revisar();
  } catch (e) {
    pintarEnvio("error", "No se pudo enviar la tecla (" + e.message + ")");
  }
}

async function revisar() {
  if (esperando === null) return;
  try {
    const r = await pedir("/teclado/estado");
    if (r.ultima_ejecutada !== null && r.ultima_ejecutada >= esperando && !r.pendientes.includes(esperando)) {
      pintarEnvio("ok", "Ejecutada en el ESP32 · mírala en el LCD");
      esperando = null;
    } else if (!r.pendientes.includes(esperando) && (r.ultima_ejecutada === null || r.ultima_ejecutada < esperando)) {
      pintarEnvio("error", "El ESP32 no la recogió a tiempo (¿está conectado?)");
      esperando = null;
    }
  } catch (e) {
    /* se reintenta en el siguiente ciclo */
  }
}

export function initTeclado() {
  const keypad = $("keypad");
  for (const [tecla, texto] of TECLAS) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tecla-btn" + (/[A-D]/.test(tecla) ? " letra" : "") + (texto ? "" : " libre");
    b.setAttribute("aria-label", texto ? `Tecla ${tecla}: ${AYUDA[tecla]}` : `Tecla ${tecla}: sin asignar`);
    b.innerHTML = `<span class="tecla-num"></span><span class="tecla-txt"></span>`;
    b.querySelector(".tecla-num").textContent = tecla;
    b.querySelector(".tecla-txt").textContent = texto || "libre";
    b.addEventListener("click", () => pulsar(tecla, b));
    keypad.append(b);
  }
  const lista = $("teclado-ayuda");
  for (const [tecla, texto] of Object.entries(AYUDA)) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="tecla" aria-hidden="true"></span><span></span>`;
    li.style.justifyContent = "flex-start";
    li.style.gap = "10px";
    li.children[0].textContent = tecla;
    li.children[1].textContent = texto;
    lista.append(li);
  }
}

/** app.js la llama al entrar / salir del módulo. */
export function iniciar() {
  detener();
  timer = setInterval(revisar, 1000);
}

export function detener() {
  clearInterval(timer);
  timer = null;
}
