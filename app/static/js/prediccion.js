// Módulo Predicción: clasifica el consumo con las reglas del taller.
import { fmt } from "./api.js";

const $ = (id) => document.getElementById(id);

const NIVELES = [
  { clase: "nivel-critico", texto: "Sobrecarga / crítico", icono: "i-alert", cumple: (p, i) => p > 600 || i > 5 },
  { clase: "nivel-alto", texto: "Consumo alto", icono: "i-alert", cumple: (p) => p > 300 },
  { clase: "nivel-normal", texto: "Consumo moderado", icono: "i-check", cumple: (p) => p > 80 },
  { clase: "nivel-bajo", texto: "Carga baja / standby", icono: "i-check", cumple: () => true },
];

export function initPrediccion() {
  const form = $("form-prediccion");
  const error = $("pred-error");
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const v = parseFloat($("pred-v").value);
    const i = parseFloat($("pred-i").value);
    if (!(v >= 0) || !(i >= 0)) {
      error.hidden = false;
      (!(v >= 0) ? $("pred-v") : $("pred-i")).focus();
      return;
    }
    error.hidden = true;
    const p = v * i;
    const nivel = NIVELES.find((n) => n.cumple(p, i));
    const caja = $("pred-resultado");
    caja.className = "result " + nivel.clase;
    caja.querySelector("use").setAttribute("href", "#" + nivel.icono);
    $("pred-categoria").textContent = nivel.texto;
    $("pred-detalle").textContent = `Potencia estimada: ${fmt(p, 1)} W`;
  });
  ["pred-v", "pred-i"].forEach((id) => $(id).addEventListener("input", () => { error.hidden = true; }));
}
