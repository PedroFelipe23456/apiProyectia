// Módulo Energía: KPIs, 5 gráficos y tabla con las mediciones del ESP32.
import { pedir, fmt, hora, token } from "./api.js";

const $ = (id) => document.getElementById(id);
const graficos = {};
let mediciones = [];   // de la más antigua a la más reciente
let resumen = null;
let lecturaVivo = null; // lo que el ESP32 manda en /motor/?v=..&i=..&p=..
let cargando = false;

// ---------------- Datos ----------------
export async function cargar() {
  if (cargando) return;
  cargando = true;
  try {
    const [lista, res] = await Promise.all([
      pedir("/mediciones/?limit=30"),
      pedir("/mediciones/resumen?limit=500"),
    ]);
    mediciones = (lista || []).slice().reverse();
    resumen = res;
    pintar();
  } catch (e) {
    mostrarEstado("error", "No se pudieron cargar las mediciones (" + e.message + ").");
  } finally {
    cargando = false;
  }
}

/** Lo llama app.js cada vez que llega /motor/estado. */
export function actualizarVivo(estado) {
  lecturaVivo = estado && estado.conectado ? estado.lectura : null;
  pintarKPIs();
}

// ---------------- Pintado ----------------
function mostrarEstado(tipo, texto) {
  const caja = $("energia-estado");
  caja.className = "card state" + (tipo === "error" ? " error" : "");
  caja.innerHTML = "";
  const icono = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icono.setAttribute("class", "icon");
  icono.innerHTML = `<use href="#${tipo === "error" ? "i-alert" : "i-inbox"}"/>`;
  const p = document.createElement("p");
  p.textContent = texto;
  caja.append(icono, p);
  if (tipo === "error") {
    const b = document.createElement("button");
    b.className = "btn";
    b.type = "button";
    b.textContent = "Reintentar";
    b.addEventListener("click", cargar);
    caja.append(b);
  }
  caja.hidden = false;
  $("energia-graficos").hidden = true;
}

function pintar() {
  pintarKPIs();
  if (!mediciones.length) {
    mostrarEstado("vacio", "Aún no hay mediciones guardadas. Pulsa el botón 2 del medidor (o la tecla del menú) para enviar una.");
    return;
  }
  $("energia-estado").hidden = true;
  $("energia-graficos").hidden = false;
  if (!window.Chart) {
    $("energia-graficos").querySelectorAll(".chart-box").forEach((c) => { c.textContent = "No se pudo cargar la librería de gráficos."; });
  } else {
    if (!graficos.gauge) crearGraficos();
    actualizarGraficos();
  }
  pintarTabla();
}

function pintarKPIs() {
  const ultima = mediciones[mediciones.length - 1];
  let v, iA, p, fuente, vivo = false;
  if (lecturaVivo) {
    v = lecturaVivo.voltaje_v; iA = lecturaVivo.corriente_ma / 1000; p = lecturaVivo.potencia_w;
    fuente = "En vivo · ESP32"; vivo = true;
  } else if (ultima) {
    v = ultima.voltaje_v; iA = ultima.corriente_a; p = ultima.potencia_w;
    fuente = "Último registro · " + hora(ultima.fecha_hora);
  } else {
    fuente = "Sin datos todavía";
  }

  $("kpi-v").textContent = fmt(v, 1);
  // Corrientes pequeñas (motor TT) se leen mejor en mA
  if (iA !== undefined && iA < 1) { $("kpi-i").textContent = fmt(iA * 1000, 0); $("kpi-i-unit").textContent = "mA"; }
  else { $("kpi-i").textContent = fmt(iA, 2); $("kpi-i-unit").textContent = "A"; }
  $("kpi-p").textContent = fmt(p, 2);
  $("kpi-e").textContent = fmt(resumen && resumen.energia_total_kwh, 4);

  $("kpi-v-foot").textContent = "Prom. " + fmt(resumen && resumen.voltaje_promedio_v, 1) + " V";
  $("kpi-i-foot").textContent = "Prom. " + fmt(resumen && resumen.corriente_promedio_a, 3) + " A";
  $("kpi-p-foot").textContent = "Máx. " + fmt(resumen && resumen.potencia_max_w, 1) + " W";
  $("kpi-e-foot").textContent = (resumen ? resumen.total : 0) + " registros";

  $("fuente-texto").textContent = fuente;
  $("fuente-lectura").classList.toggle("live", vivo);

  if (graficos.gauge && p !== undefined) actualizarGauge(p);
}

function pintarTabla() {
  const cuerpo = $("tabla-mediciones");
  cuerpo.innerHTML = "";
  mediciones.slice(-10).reverse().forEach((m) => {
    const tr = document.createElement("tr");
    [hora(m.fecha_hora), fmt(m.voltaje_v, 1), fmt(m.corriente_a, 3), fmt(m.potencia_w, 2)].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.append(td);
    });
    cuerpo.append(tr);
  });
  $("tabla-nota").textContent = "Mostrando " + Math.min(10, mediciones.length) + " de " + (resumen ? resumen.total : mediciones.length);
}

// ---------------- Gráficos (Chart.js) ----------------
function colores() {
  return {
    c1: token("--chart-1"), c2: token("--chart-2"), c3: token("--chart-3"),
    track: token("--chart-track"), grid: token("--chart-grid"),
    texto: token("--text-muted"), danger: token("--danger"), ok: token("--ok"), warn: token("--warn"),
  };
}

function ejes(c, extra = {}) {
  return {
    x: { ticks: { color: c.texto, maxRotation: 0, autoSkip: true, maxTicksLimit: 5 }, grid: { color: c.grid } },
    y: { ticks: { color: c.texto }, grid: { color: c.grid }, ...extra },
  };
}

function crearGraficos() {
  const c = colores();
  Chart.defaults.font.family = token("--font-sans") || "sans-serif";
  Chart.defaults.font.size = 12;
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  Chart.defaults.animation = reducido ? false : { duration: 250 };

  graficos.gauge = new Chart($("g-gauge"), {
    type: "doughnut",
    data: { labels: ["Potencia (W)", "Restante"], datasets: [{ data: [0, 1], backgroundColor: [c.c1, c.track], borderWidth: 0 }] },
    options: { maintainAspectRatio: false, rotation: -90, circumference: 180, cutout: "78%", plugins: { legend: { display: false }, tooltip: { enabled: false } } },
  });

  graficos.vi = new Chart($("g-vi"), {
    type: "line",
    data: { labels: [], datasets: [
      { label: "Voltaje (V)", data: [], borderColor: c.c1, backgroundColor: c.c1, yAxisID: "y", borderWidth: 2, pointRadius: 0, tension: .3 },
      { label: "Corriente (A)", data: [], borderColor: c.c2, backgroundColor: c.c2, yAxisID: "y1", borderWidth: 2, pointRadius: 0, tension: .3, borderDash: [6, 4] },
    ] },
    options: {
      maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: c.texto, boxWidth: 12 } } },
      scales: { ...ejes(c), y1: { position: "right", grid: { drawOnChartArea: false }, ticks: { color: c.texto } } },
    },
  });

  graficos.potencia = new Chart($("g-potencia"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Potencia (W)", data: [], backgroundColor: c.c1, borderRadius: 4 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: ejes(c, { beginAtZero: true }) },
  });

  graficos.voltaje = new Chart($("g-voltaje"), {
    type: "bar",
    data: { labels: ["Mínimo", "Promedio", "Máximo"], datasets: [{ label: "Voltaje (V)", data: [0, 0, 0], backgroundColor: [c.c3, c.c1, c.c2], borderRadius: 4 }] },
    options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: ejes(c) },
  });

  graficos.corriente = new Chart($("g-corriente"), {
    type: "doughnut",
    data: { labels: ["Baja (< 2 A)", "Media (2–4,5 A)", "Alta (> 4,5 A)"], datasets: [{ data: [0, 0, 0], backgroundColor: [c.c3, c.c1, c.danger], borderWidth: 0 }] },
    options: { maintainAspectRatio: false, cutout: "60%", plugins: { legend: { position: "bottom", labels: { color: c.texto, boxWidth: 12 } } } },
  });
}

function actualizarGauge(p) {
  const maximo = Math.max(10, (resumen && resumen.potencia_max_w ? resumen.potencia_max_w : p) * 1.2, p);
  graficos.gauge.data.datasets[0].data = [Math.max(0, p), Math.max(0, maximo - p)];
  graficos.gauge.update();
  $("gauge-valor").textContent = fmt(p, 2);
}

function actualizarGraficos() {
  const etiquetas = mediciones.map((m) => hora(m.fecha_hora));
  const vs = mediciones.map((m) => Number(m.voltaje_v));
  const is = mediciones.map((m) => Number(m.corriente_a));
  const ps = mediciones.map((m) => Number(m.potencia_w));

  graficos.vi.data.labels = etiquetas;
  graficos.vi.data.datasets[0].data = vs;
  graficos.vi.data.datasets[1].data = is;
  graficos.vi.update();

  graficos.potencia.data.labels = etiquetas;
  graficos.potencia.data.datasets[0].data = ps;
  graficos.potencia.update();

  const prom = vs.reduce((a, b) => a + b, 0) / vs.length;
  graficos.voltaje.data.datasets[0].data = [Math.min(...vs), Number(prom.toFixed(2)), Math.max(...vs)];
  graficos.voltaje.update();

  graficos.corriente.data.datasets[0].data = [
    is.filter((x) => x < 2).length,
    is.filter((x) => x >= 2 && x <= 4.5).length,
    is.filter((x) => x > 4.5).length,
  ];
  graficos.corriente.update();

  const ultima = lecturaVivo ? lecturaVivo.potencia_w : ps[ps.length - 1];
  actualizarGauge(ultima);
}

/** Recolorea los gráficos al cambiar entre modo claro y oscuro. */
export function aplicarTema() {
  if (!graficos.gauge) return;
  const c = colores();
  graficos.gauge.data.datasets[0].backgroundColor = [c.c1, c.track];
  graficos.vi.data.datasets[0].borderColor = graficos.vi.data.datasets[0].backgroundColor = c.c1;
  graficos.vi.data.datasets[1].borderColor = graficos.vi.data.datasets[1].backgroundColor = c.c2;
  graficos.potencia.data.datasets[0].backgroundColor = c.c1;
  graficos.voltaje.data.datasets[0].backgroundColor = [c.c3, c.c1, c.c2];
  graficos.corriente.data.datasets[0].backgroundColor = [c.c3, c.c1, c.danger];
  for (const g of Object.values(graficos)) {
    const s = g.options.scales || {};
    for (const eje of Object.values(s)) {
      if (eje.ticks) eje.ticks.color = c.texto;
      if (eje.grid && eje.grid.color) eje.grid.color = c.grid;
    }
    if (g.options.plugins.legend && g.options.plugins.legend.labels) g.options.plugins.legend.labels.color = c.texto;
    g.update();
  }
}
