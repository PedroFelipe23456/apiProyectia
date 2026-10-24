// Módulo Predicción: clasifica el estado de la carga con el modelo de Edge Impulse (POST /predecir).
const $ = (id) => document.getElementById(id);

const CATEGORIAS = {
  reposo:     { clase: "nivel-bajo",    texto: "Reposo",     icono: "i-check" },
  normal:     { clase: "nivel-normal",  texto: "Normal",     icono: "i-check" },
  alta:       { clase: "nivel-alto",    texto: "Alta",       icono: "i-alert" },
  sobrecarga: { clase: "nivel-critico", texto: "Sobrecarga", icono: "i-alert" },
};

export function initPrediccion() {
  const form = $("form-prediccion");
  const error = $("pred-error");
  const boton = form.querySelector("button[type=submit]");

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const v = parseFloat($("pred-v").value);
    const i = parseFloat($("pred-i").value);
    if (!(v >= 0) || !(i >= 0)) {
      error.hidden = false;
      (!(v >= 0) ? $("pred-v") : $("pred-i")).focus();
      return;
    }
    error.hidden = true;

    const p = Math.round(v * i * 100) / 100;
    const caja = $("pred-resultado");
    $("pred-categoria").textContent = "Consultando al modelo…";
    $("pred-detalle").textContent = "";
    boton.disabled = true;

    try {
      const res = await fetch("/predecir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voltaje: v, corriente: i, potencia: p }),
      });
      const datos = await res.json();
      if (!res.ok) throw new Error(datos.detail || "Error " + res.status);

      const cat = CATEGORIAS[datos.categoria] || CATEGORIAS.normal;
      caja.className = "result " + cat.clase;
      caja.querySelector("use").setAttribute("href", "#" + cat.icono);
      $("pred-categoria").textContent = cat.texto;
      $("pred-detalle").textContent =
        `Confianza: ${datos.confianza} % · Potencia calculada: ${p} W`;
    } catch (err) {
      $("pred-categoria").textContent = "No se pudo predecir";
      $("pred-detalle").textContent = String(err.message || err);
    } finally {
      boton.disabled = false;
    }
  });

  ["pred-v", "pred-i"].forEach((id) =>
    $(id).addEventListener("input", () => { error.hidden = true; })
  );
}