from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Predicción IA"])


class EntradaPrediccion(BaseModel):
    voltaje: float
    corriente: float
    potencia: float


@router.post("/predecir")
def predecir_estado(datos: EntradaPrediccion):
    # Se importa aquí para que, si el modelo falla al cargar,
    # el resto de la API siga funcionando.
    try:
        from app.predictor import predecir
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Modelo no disponible: {e}")

    resultado = predecir(datos.voltaje, datos.corriente, datos.potencia)
    resultado["entrada"] = datos.model_dump()
    return resultado