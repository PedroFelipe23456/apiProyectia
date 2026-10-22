// Shell de la aplicación: acceso, navegación por módulos (#energia, #motor,
// #prediccion), tema claro/oscuro y consulta del estado del ESP32.
import { pedir } from "./api.js";
import * as energia from "./energia.js";
import * as motor from "./motor.js";
import { initPrediccion } from "./prediccion.js";

const $ = (id) => document.getElementById(id);
const RUTAS = ["energia", "motor", "prediccion"];
let rutaActual = null;
let timerEstado = null;
let timerEnergia = null;

// ---------------- Sesión (demo, sin validación real) ----------------
function haySesion() {
  try { return sessionStorage.getItem("pm-sesion") === "1"; } catch (e) { return false; }
}

function entrar() {
  try { sessionStorage.setItem("pm-sesion", "1"); } catch (e) { /* modo privado */ }
  $("vista-login").hidden = true;
  $("vista-app").hidden = false;
  if (!location.hash) location.hash = "#energia";
  navegar();
  consultarEstado();
  timerEstado = setInterval(consultarEstado, 2000);
}

function salir() {
  try { sessionStorage.removeItem("pm-sesion"); } catch (e) { /* nada */ }
  clearInterval(timerEstado);
  clearInterval(timerEnergia);
  $("vista-app").hidden = true;
  $("vista-login").hidden = false;
  $("login-usuario").focus();
}

$("form-login").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const ok = $("login-usuario").value.trim() && $("login-clave").value;
  $("login-error").hidden = Boolean(ok);
  if (ok) entrar();
  else (!$("login-usuario").value.trim() ? $("login-usuario") : $("login-clave")).focus();
});
$("btn-salir").addEventListener("click", salir);

// ---------------- Navegación ----------------
function navegar() {
  if ($("vista-app").hidden) return;
  const ruta = RUTAS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "energia";
  if (ruta === rutaActual) return;
  rutaActual = ruta;
  document.querySelectorAll("[data-vista]").forEach((s) => { s.hidden = s.dataset.vista !== ruta; });
  document.querySelectorAll(".nav a").forEach((a) => {
    if (a.dataset.ruta === ruta) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  document.title = { energia: "Energía", motor: "Motor", prediccion: "Predicción" }[ruta] + " · PowerMonitor IoT";
  $("titulo-" + ruta).focus({ preventScroll: true });
  window.scrollTo(0, 0);

  // Las mediciones solo se consultan mientras el módulo Energía está abierto
  clearInterval(timerEnergia);
  if (ruta === "energia") {
    energia.cargar();
    timerEnergia = setInterval(energia.cargar, 5000);
  }
}
window.addEventListener("hashchange", navegar);

// ---------------- Estado del ESP32 (compartido) ----------------
async function consultarEstado() {
  if (motor.estaArrastrando()) return;
  const pill = $("pill-esp32");
  try {
    const r = await pedir("/motor/estado");
    pill.classList.toggle("on", r.conectado);
    pill.classList.toggle("off", !r.conectado);
    $("pill-esp32-texto").textContent = r.conectado ? "ESP32 conectado" : "ESP32 desconectado";
    motor.actualizarEstado(r);
    energia.actualizarVivo(r);
  } catch (e) {
    pill.classList.remove("on");
    pill.classList.add("off");
    $("pill-esp32-texto").textContent = "Sin servidor";
  }
}

// ---------------- Tema ----------------
function pintarBotonTema() {
  const claro = document.documentElement.dataset.theme === "light";
  $("icono-tema").setAttribute("href", claro ? "#i-moon" : "#i-sun");
  $("btn-tema").setAttribute("aria-label", claro ? "Cambiar a modo oscuro" : "Cambiar a modo claro");
}
$("btn-tema").addEventListener("click", () => {
  const nuevo = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = nuevo;
  try { localStorage.setItem("pm-tema", nuevo); } catch (e) { /* nada */ }
  pintarBotonTema();
  energia.aplicarTema();
});

// ---------------- Arranque ----------------
motor.initMotor();
initPrediccion();
pintarBotonTema();
if (haySesion()) entrar();
