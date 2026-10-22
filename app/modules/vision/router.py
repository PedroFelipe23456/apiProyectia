import io
import os
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from PIL import Image

router = APIRouter(prefix="/vision", tags=["Vision YOLOv8"])

# Pesos del modelo, en la misma carpeta que este módulo
MODEL_PATH = os.path.join(os.path.dirname(__file__), "best.pt")

_yolo_model = None


def obtener_modelo():
    """
    Carga YOLO la primera vez que se usa (no al arrancar la API).
    Así la API arranca rápido y el resto de módulos funciona aunque
    ultralytics no esté instalado o el modelo falle.
    """
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO(MODEL_PATH)
        except Exception as e:
            print(f"Advertencia: No se pudo cargar el modelo YOLO en {MODEL_PATH}: {e}")
    return _yolo_model


@router.post("/detectar", status_code=status.HTTP_200_OK)
async def detectar_estado_carga(file: UploadFile = File(...)):
    """
    Recibe una imagen (JPG/PNG) y retorna las detecciones de YOLOv8:
    - Estado de los focos ('foco_encendido', 'foco_apagado')
    - Presencia de personas ('persona')
    """
    yolo_model = obtener_modelo()
    if not yolo_model:
        raise HTTPException(
            status_code=500, 
            detail="El modelo YOLO ('best.pt') no esta cargado en el servidor."
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, 
            detail="El archivo enviado debe ser una imagen (JPEG/PNG)."
        )

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    results = yolo_model(image, conf=0.15)

    detecciones = []
    foco_encendido = False
    foco_apagado = False
    persona_detectada = False

    for r in results:
        for box in r.boxes:
            class_id = int(box.cls[0])
            class_name = yolo_model.names[class_id]
            confidence = float(box.conf[0])

            if class_name == "foco_encendido":
                foco_encendido = True
            elif class_name == "foco_apagado":
                foco_apagado = True
            elif class_name == "persona":
                persona_detectada = True

            detecciones.append({
                "clase": class_name,
                "confianza": round(confidence, 4)
            })

    return {
        "resumen": {
            "foco_encendido": foco_encendido,
            "foco_apagado": foco_apagado,
            "persona_detectada": persona_detectada,
            "total_objetos": len(detecciones)
        },
        "detecciones": detecciones
    }