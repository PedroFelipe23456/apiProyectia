from pathlib import Path
import numpy as np
from ai_edge_litert.interpreter import Interpreter

SCALE_AXES = 0.01
# Edge Impulse ordena las clases alfabéticamente
CLASES = ["alta", "normal", "reposo", "sobrecarga"]

RUTA_MODELO = Path(__file__).parent / "modelo" / "modelo.tflite"

_interp = Interpreter(model_path=str(RUTA_MODELO))
_interp.allocate_tensors()
_inp = _interp.get_input_details()[0]
_out = _interp.get_output_details()[0]

def predecir(voltaje: float, corriente: float, potencia: float) -> dict:
    x = np.array([[voltaje, corriente, potencia]], dtype=np.float32) * SCALE_AXES
    if _inp["dtype"] == np.int8:  # por si se usa el modelo int8
        escala, cero = _inp["quantization"]
        x = np.round(x / escala + cero).astype(np.int8)
    _interp.set_tensor(_inp["index"], x)
    _interp.invoke()
    y = _interp.get_tensor(_out["index"])[0].astype(np.float32)
    if _out["dtype"] == np.int8:
        escala, cero = _out["quantization"]
        y = (y - cero) * escala
    i = int(np.argmax(y))
    return {
        "categoria": CLASES[i],
        "confianza": round(float(y[i]) * 100, 2),
        "probabilidades": {c: round(float(p), 4) for c, p in zip(CLASES, y)},
    }