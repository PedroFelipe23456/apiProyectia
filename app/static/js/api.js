// Utilidades compartidas por todos los módulos de la web.
// Todas las URLs son relativas: funcionan igual en local y en Render.

let pendientes = 0;

/**
 * fetch con JSON. Si la respuesta tarda más de 3 s muestra el aviso
 * "Despertando el servidor" (el plan gratis de Render se duerme).
 */
export async function pedir(url, opciones = {}) {
  const aviso = document.getElementById("aviso-servidor");
  pendientes++;
  const temporizador = setTimeout(() => { aviso.hidden = false; }, 3000);
  try {
    const r = await fetch(url, { cache: "no-store", ...opciones });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.status === 204 ? null : await r.json();
  } finally {
    clearTimeout(temporizador);
    if (--pendientes === 0) aviso.hidden = true;
  }
}

export function enviarJSON(url, metodo, cuerpo) {
  return pedir(url, {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

const nf = (d) => new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });

/** Formatea un número con `d` decimales; "--" si no hay valor. */
export function fmt(valor, d = 1) {
  return valor === null || valor === undefined || Number.isNaN(Number(valor)) ? "--" : nf(d).format(Number(valor));
}

/** "2026-10-22T21:22:55.123" -> "21:22:55" */
export function hora(fechaIso) {
  if (!fechaIso) return "";
  const s = String(fechaIso).replace(" ", "T");
  return s.includes("T") ? s.split("T")[1].slice(0, 8) : s;
}

let toastTimer = null;
export function toast(mensaje) {
  const t = document.getElementById("toast");
  t.textContent = mensaje;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
}

/** Lee un color del tema actual (tokens CSS). */
export function token(nombre) {
  return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
}
