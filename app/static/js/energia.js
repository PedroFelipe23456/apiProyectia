// Módulo Energía: KPIs, 5 gráficos y tabla.
// Dos modos:
//   - En vivo:   lecturas que el ESP32 manda cada ~1 s (/mediciones/vivo), refresco cada 1 s.
//   - Historial: mediciones guardadas en la base de datos (/mediciones/), refresco cada 5 s.
import { pedir, fmt, hora, token } from "./api.js";

const $ = (id) => document.getElementById(id);
const graficos = {};
const INTERVALO = { vivo: 1000, historial: 5000 };

// Niveles de potencia: los mismos que usan los LEDs del medidor (actualizarLeds en el sketch)
const NIVEL_MEDIO_W = 5;
const NIVEL_ALTO_W = 15;
// Escalas "redondas" para el arco: se elige la menor que cubra el máximo de la ventana
const ESCALAS_W = [1, 2, 5, 10, 15, 20, 50, 100, 200, 500, 1000, 2000];

// Rangos de corriente para el gráfico "Clasificación por corriente", pensados para
// el motor TT 1:48 (sin carga ~150 mA, frenado > 1 A). Ajústalos si cambias de carga.
const RANGOS_CORRIENTE = [
  { nombre: "Detenido", hasta: 0.1, texto: "< 0,1 A" },
  { nombre: "Normal", hasta: 0.5, texto: "0,1–0,5 A" },
  { nombre: "Alto", hasta: 1.0, texto: "0,5–1 A" },
  { nombre: "Sobrecarga", hasta: Infinity, texto: "≥ 1 A" },
];

let modo = "vivo";
let pausado = false;
let timer = null;
let cargando = false;
let ticks = 0;
let puntos = [];        // [{etiqueta, voltaje_v, corriente_a, potencia_w}] del más antiguo al más reciente
let resumenBD = null;   // /mediciones/resumen (energía acumulada y totales de la base de datos)
let menuBD = null;      // /mediciones/menu (opciones 2-6 y 9 del teclado)
let conectado = false;

// ---------------- Ciclo de actualización ----------------
export function iniciar() {
  detener();
  cargar();
  if (!pausado) timer = setInterval(cargar, INTERVALO[modo]);
}

export function detener() {
  clearInterval(timer);
  timer = null;
}

async function cargar() {
  if (cargando) return;
  cargando = true;
  const modoPedido = modo;
  try {
    // El resumen de la base de datos cambia poco: en vivo se pide cada 10 s
    const pedirResumen = modo === "historial" || ticks % 10 === 0 || !resumenBD;
    const [datos, res, menu] = await Promise.all([
      modo === "vivo" ? pedir("/mediciones/vivo?n=120") : pedir("/mediciones/?limit=30"),
      pedirResumen ? pedir("/mediciones/resumen?limit=500") : Promise.resolve(resumenBD),
      pedirResumen ? pedir("/mediciones/menu") : Promise.resolve(menuBD),
    ]);
    // Si el usuario cambió de modo mientras llegaba la respuesta, se descarta
    if (modoPedido !== modo) return;
    resumenBD = res;
    menuBD = menu;
    pintarMenu();
    puntos = modo === "vivo"
      ? datos.map((p) => ({ ...p, etiqueta: horaLocal(p.ts) }))
      : datos.slice().reverse().map((m) => ({
          etiqueta: hora(m.fecha_hora), voltaje_v: Number(m.voltaje_v),
          corriente_a: Number(m.corriente_a), potencia_w: Number(m.potencia_w),
        }));
    ticks++;
    pintar();
  } catch (e) {
    if (modoPedido === modo) mostrarEstado("error", "No se pudieron cargar las mediciones (" + e.message + ").");
  } finally {
    cargando = false;
    // Si se cambió de modo durante la petición, carga ya el modo nuevo
    if (modoPedido !== modo) cargar();
  }
}

/** Lo llama app.js cada vez que llega /motor/estado. */
export function actualizarConexion(estado) {
  conectado = Boolean(estado && estado.conectado);
}

function horaLocal(ms) {
  return new Date(ms).toLocaleTimeString("es-CO", { hour12: false });
}

// ---------------- Controles ----------------
export function initEnergia() {
  $("modo-vivo").addEventListener("click", () => cambiarModo("vivo"));
  $("modo-historial").addEventListener("click", () => cambiarModo("historial"));
  $("btn-pausa").addEventListener("click", () => {
    pausado = !pausado;
    $("btn-pausa").setAttribute("aria-pressed", String(pausado));
    $("btn-pausa").setAttribute("aria-label", pausado ? "Reanudar actualización" : "Pausar actualización");
    $("icono-pausa").setAttribute("href", pausado ? "#i-play" : "#i-pause");
    if (pausado) detener(); else iniciar();
    pintarFuente();
  });
}

function cambiarModo(nuevo) {
  if (nuevo === modo) return;
  modo = nuevo;
  $("modo-vivo").setAttribute("aria-pressed", String(modo === "vivo"));
  $("modo-historial").setAttribute("aria-pressed", String(modo === "historial"));
  puntos = [];
  iniciar();
}

// ---------------- Pintado ----------------
function mostrarEstado(tipo, texto) {
  const caja = $("energia-estado");
  caja.className = "card state" + (tipo === "error" ? " error" : "");
  caja.innerHTML = "";
  const icono = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icono.setAttribute("class", "icon");
  icono.innerHTML = `<use href="#${tipo === "error" ? "i-alert" : tipo === "espera" ? "i-wifi" : "i-inbox"}"/>`;
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
  pintarFuente();
  if (!puntos.length) {
    if (modo === "vivo") {
      mostrarEstado("espera", conectado
        ? "Esperando la primera lectura del ESP32…"
        : "Esperando lecturas del ESP32. Revisa que arriba diga «ESP32 conectado».");
    } else {
      mostrarEstado("vacio", "Aún no hay mediciones guardadas. Pulsa el botón 2 del medidor (o la tecla del menú) para enviar una.");
    }
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

function estadisticas() {
  if (!puntos.length) return null;
  const media = (k) => puntos.reduce((a, p) => a + p[k], 0) / puntos.length;
  return {
    vProm: media("voltaje_v"),
    iProm: media("corriente_a"),
    pMax: Math.max(...puntos.map((p) => p.potencia_w)),
  };
}

function pintarKPIs() {
  const ultima = puntos[puntos.length - 1];
  const est = estadisticas();
  const iA = ultima ? ultima.corriente_a : undefined;

  $("kpi-v").textContent = fmt(ultima && ultima.voltaje_v, 1);
  // Corrientes pequeñas (motor TT) se leen mejor en mA
  if (iA !== undefined && iA < 1) { $("kpi-i").textContent = fmt(iA * 1000, 0); $("kpi-i-unit").textContent = "mA"; }
  else { $("kpi-i").textContent = fmt(iA, 2); $("kpi-i-unit").textContent = "A"; }
  $("kpi-p").textContent = fmt(ultima && ultima.potencia_w, 2);
  $("kpi-e").textContent = fmt(resumenBD && resumenBD.energia_total_kwh, 4);

  const ventana = modo === "vivo" ? "ventana" : "registros";
  $("kpi-v-foot").textContent = `Prom. ${ventana} ${fmt(est && est.vProm, 1)} V`;
  $("kpi-i-foot").textContent = `Prom. ${ventana} ${fmt(est && est.iProm, 3)} A`;
  $("kpi-p-foot").textContent = `Máx. ${ventana} ${fmt(est && est.pMax, 2)} W`;
  $("kpi-e-foot").textContent = (resumenBD ? resumenBD.total : 0) + " registros guardados";
}

function pintarFuente() {
  const vivo = modo === "vivo" && !pausado && conectado && puntos.length > 0;
  let texto;
  if (pausado) texto = "Pausado";
  else if (modo === "vivo") texto = vivo ? `En vivo · ESP32 · ${puntos.length} lecturas` : "En vivo · esperando al ESP32";
  else texto = puntos.length ? `Historial · último registro ${puntos[puntos.length - 1].etiqueta}` : "Historial · sin registros";
  $("fuente-texto").textContent = texto;
  $("fuente-lectura").classList.toggle("live", vivo);
  $("nota-potencia").textContent = modo === "vivo" ? "W · cada segundo" : "W · registros guardados";
}

/** Tarjeta "Menú del teclado": los mismos cálculos que muestra el LCD. */
function pintarMenu() {
  if (!menuBD) return;
  const u = menuBD.ultimo;
  const d = menuBD.ultimas_24h;
  const h = menuBD.ultima_hora;
  $("menu-ultimo").textContent = u ? `${fmt(u.voltaje_v, 1)} V · ${fmt(u.potencia_w, 2)} W` : "Sin registros";
  $("menu-ultimo-hora").textContent = u ? hora(u.fecha_hora).slice(0, 5) : "";
  $("menu-prom24").textContent = d.registros ? `${fmt(d.promedio_w, 2)} W` : "Sin registros";
  $("menu-maxmin").textContent = d.registros ? `${fmt(d.max_w, 2)} / ${fmt(d.min_w, 2)} W` : "Sin registros";
  $("menu-promh").textContent = h.registros ? `${fmt(h.promedio_w, 2)} W` : "Sin registros";
  $("menu-regs").textContent = String(d.registros);
  $("menu-sd").textContent = menuBD.desviacion_w === null ? "Pocos registros" : `${fmt(menuBD.desviacion_w, 2)} W`;
}

function pintarTabla() {
  const cuerpo = $("tabla-mediciones");
  cuerpo.innerHTML = "";
  puntos.slice(-10).reverse().forEach((m) => {
    const tr = document.createElement("tr");
    [m.etiqueta, fmt(m.voltaje_v, 2), fmt(m.corriente_a, 3), fmt(m.potencia_w, 3)].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.append(td);
    });
    cuerpo.append(tr);
  });
  $("tabla-nota").textContent = modo === "vivo"
    ? "Lecturas en vivo (no se guardan)"
    : `Mostrando ${Math.min(10, puntos.length)} de ${resumenBD ? resumenBD.total : puntos.length}`;
}

// ---------------- Gráficos (Chart.js) ----------------
function colores() {
  return {
    c1: token("--chart-1"), c2: token("--chart-2"), c3: token("--chart-3"),
    track: token("--chart-track"), grid: token("--chart-grid"),
    texto: token("--text-muted"), danger: token("--danger"), warn: token("--warn"), ok: token("--ok"),
  };
}

/** Degradado arcoíris de izquierda (0 W, verde) a derecha (máximo, rojo) para el arco. */
function degradadoArco(chart) {
  const area = chart.chartArea;
  const c = colores();
  if (!area) return c.ok;
  const g = chart.ctx.createLinearGradient(area.left, 0, area.right, 0);
  g.addColorStop(0, c.ok);
  g.addColorStop(0.5, c.warn);
  g.addColorStop(1, c.danger);
  return g;
}

function coloresCorriente(c) {
  return [c.c3, c.c1, c.warn, c.danger];
}

/** Cuenta cuántas lecturas caen en cada rango de RANGOS_CORRIENTE. */
function clasificarCorriente(corrientes) {
  const cuentas = RANGOS_CORRIENTE.map(() => 0);
  for (const x of corrientes) {
    cuentas[RANGOS_CORRIENTE.findIndex((r) => x < r.hasta)]++;
  }
  return cuentas;
}

// Marca solo el último punto de cada línea: así se ve llegar cada lectura nueva
const ultimoPunto = (ctx) => (ctx.dataIndex === ctx.dataset.data.length - 1 ? 4 : 0);

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
  // Sin animaciones: los datos llegan cada segundo y cada actualización se dibuja al instante.
  // Con animación, Chart.js pinta en cuadros (requestAnimationFrame); al reiniciarla cada
  // segundo, en algunos navegadores nunca terminaba y las gráficas quedaban en blanco.
  Chart.defaults.animation = false;

  graficos.gauge = new Chart($("g-gauge"), {
    type: "doughnut",
    data: {
      labels: ["Potencia (W)", "Restante"],
      datasets: [{
        data: [0, 1],
        // El tramo lleno se pinta con el degradado arcoíris; el resto es la pista gris
        backgroundColor: (ctx) => (ctx.dataIndex === 0 ? degradadoArco(ctx.chart) : colores().track),
        borderWidth: 0,
      }],
    },
    options: {
      maintainAspectRatio: false, rotation: -90, circumference: 180, cutout: "74%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });

  graficos.vi = new Chart($("g-vi"), {
    type: "line",
    data: { labels: [], datasets: [
      { label: "Voltaje (V)", data: [], borderColor: c.c1, backgroundColor: c.c1, yAxisID: "y", borderWidth: 2, pointRadius: ultimoPunto, tension: .3 },
      { label: "Corriente (A)", data: [], borderColor: c.c2, backgroundColor: c.c2, yAxisID: "y1", borderWidth: 2, pointRadius: ultimoPunto, tension: .3, borderDash: [6, 4] },
    ] },
    options: {
      maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: c.texto, boxWidth: 12 } } },
      // grace: margen arriba y abajo para que la línea no quede pegada al borde
      scales: {
        ...ejes(c, { grace: "15%", title: { display: true, text: "V", color: c.texto } }),
        y1: { position: "right", grace: "15%", grid: { drawOnChartArea: false }, ticks: { color: c.texto }, title: { display: true, text: "A", color: c.texto } },
      },
    },
  });

  graficos.potencia = new Chart($("g-potencia"), {
    type: "line",
    data: { labels: [], datasets: [{ label: "Potencia (W)", data: [], borderColor: c.c1, backgroundColor: c.c1 + "33", fill: true, borderWidth: 2, pointRadius: ultimoPunto, tension: .3 }] },
    options: { maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { display: false } }, scales: ejes(c, { beginAtZero: true }) },
  });

  graficos.voltaje = new Chart($("g-voltaje"), {
    type: "bar",
    data: { labels: ["Mínimo", "Promedio", "Máximo"], datasets: [{ label: "Voltaje (V)", data: [0, 0, 0], backgroundColor: [c.c3, c.c1, c.c2], borderRadius: 4 }] },
    // El eje no empieza en 0: así se notan diferencias pequeñas entre mín, prom y máx
    options: {
      indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { ...ejes(c), x: { ...ejes(c).x, beginAtZero: false, grace: "60%" } },
    },
  });

  graficos.corriente = new Chart($("g-corriente"), {
    type: "doughnut",
    data: {
      labels: RANGOS_CORRIENTE.map((r) => `${r.nombre} (${r.texto})`),
      datasets: [{ data: RANGOS_CORRIENTE.map(() => 0), backgroundColor: coloresCorriente(c), borderWidth: 0 }],
    },
    options: {
      maintainAspectRatio: false, cutout: "60%",
      plugins: {
        legend: { position: "bottom", labels: { color: c.texto, boxWidth: 12 } },
        tooltip: { callbacks: { label: (ctx) => ` ${ctx.parsed} lecturas` } },
      },
    },
  });
}

/** Redibuja de inmediato (sin animación); si algo falla, no frena las demás gráficas. */
function redibujar(g) {
  try {
    g.update("none");
  } catch (e) {
    console.error("No se pudo dibujar la gráfica", g.canvas.id, e);
  }
}

function actualizarGraficos() {
  const etiquetas = puntos.map((p) => p.etiqueta);
  const vs = puntos.map((p) => p.voltaje_v);
  const is = puntos.map((p) => p.corriente_a);
  const ps = puntos.map((p) => p.potencia_w);

  graficos.vi.data.labels = etiquetas;
  graficos.vi.data.datasets[0].data = vs;
  graficos.vi.data.datasets[1].data = is;
  redibujar(graficos.vi);

  graficos.potencia.data.labels = etiquetas;
  graficos.potencia.data.datasets[0].data = ps;
  redibujar(graficos.potencia);

  const prom = vs.reduce((a, b) => a + b, 0) / vs.length;
  const vMin = Math.min(...vs);
  const vMax = Math.max(...vs);
  graficos.voltaje.data.datasets[0].data = [vMin, Number(prom.toFixed(2)), vMax];
  redibujar(graficos.voltaje);
  $("nota-voltaje").textContent = `${fmt(vMin, 2)} · ${fmt(prom, 2)} · ${fmt(vMax, 2)} V`;

  // La cantidad va en la leyenda para que se lea sin pasar el mouse por encima
  const cuentas = clasificarCorriente(is);
  graficos.corriente.data.labels = RANGOS_CORRIENTE.map((r, k) => `${r.nombre} (${r.texto}): ${cuentas[k]}`);
  graficos.corriente.data.datasets[0].data = cuentas;
  redibujar(graficos.corriente);

  actualizarGauge(ps[ps.length - 1], Math.max(...ps));
}

/** Arco arcoíris: escala redonda estable y nivel según los umbrales de los LEDs. */
function actualizarGauge(actual, maxVentana) {
  const escala = ESCALAS_W.find((e) => e >= maxVentana * 1.1) || ESCALAS_W[ESCALAS_W.length - 1];
  const valor = Math.min(Math.max(0, actual), escala);
  graficos.gauge.data.datasets[0].data = [valor, escala - valor];
  redibujar(graficos.gauge);
  $("gauge-valor").textContent = fmt(actual, 2);
  $("gauge-max").textContent = `${fmt(escala, 0)} W`;

  const nivel = $("gauge-nivel");
  const [clase, texto] = actual >= NIVEL_ALTO_W
    ? ["alto", `Nivel alto (≥ ${NIVEL_ALTO_W} W)`]
    : actual >= NIVEL_MEDIO_W
      ? ["medio", `Nivel medio (${NIVEL_MEDIO_W}–${NIVEL_ALTO_W} W)`]
      : ["bajo", `Nivel bajo (< ${NIVEL_MEDIO_W} W)`];
  nivel.className = "gauge-nivel " + clase;
  nivel.textContent = texto;
}

/** Recolorea los gráficos al cambiar entre modo claro y oscuro. */
export function aplicarTema() {
  if (!graficos.gauge) return;
  const c = colores();
  graficos.vi.data.datasets[0].borderColor = graficos.vi.data.datasets[0].backgroundColor = c.c1;
  graficos.vi.data.datasets[1].borderColor = graficos.vi.data.datasets[1].backgroundColor = c.c2;
  graficos.potencia.data.datasets[0].borderColor = c.c1;
  graficos.potencia.data.datasets[0].backgroundColor = c.c1 + "33";
  graficos.voltaje.data.datasets[0].backgroundColor = [c.c3, c.c1, c.c2];
  graficos.corriente.data.datasets[0].backgroundColor = coloresCorriente(c);
  for (const g of Object.values(graficos)) {
    const s = g.options.scales || {};
    for (const eje of Object.values(s)) {
      if (eje.ticks) eje.ticks.color = c.texto;
      if (eje.grid && eje.grid.color) eje.grid.color = c.grid;
      if (eje.title) eje.title.color = c.texto;
    }
    if (g.options.plugins.legend && g.options.plugins.legend.labels) g.options.plugins.legend.labels.color = c.texto;
    redibujar(g);
  }
}
