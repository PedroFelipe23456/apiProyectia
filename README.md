# API Taller 1 — Medición de potencia con ACS712

API REST en Python (FastAPI + SQLAlchemy) con estructura POO que expone
CRUD completo sobre las 14 tablas creadas en `taller1_basedatos.sql`.

## Estructura del proyecto

```
app/
  database.py              # Conexión a PostgreSQL (SQLAlchemy)
  models.py                # Entidades ORM (una clase por tabla)
  schemas.py                # Validación Pydantic (Create/Read por entidad)
  repository.py             # BaseRepository genérico + repos por entidad (herencia)
  crud_router.py            # CRUDRouter genérico -> arma las 5 rutas REST
  reporte_detalle_router.py # Router especial (llave primaria compuesta)
  main.py                   # Punto de entrada, registra todos los routers
requirements.txt
.env.example
```

## 1. Instalación

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar la base de datos

1. Copia `.env.example` a `.env`.
2. Reemplaza `DATABASE_URL` con la cadena de conexión de tu PostgreSQL
   en la nube (la misma donde corriste `taller1_basedatos.sql`).

```
DATABASE_URL=postgresql://usuario:password@host:5432/taller1_db
```

> La API **no crea las tablas** (`Base.metadata.create_all` no se llama):
> se asume que ya ejecutaste el script SQL de la Parte 1. Esto evita
> tener el esquema definido en dos lugares distintos.

## 3. Ejecutar

```bash
uvicorn app.main:app --reload
```

Documentación interactiva (Swagger) en `http://127.0.0.1:8000/docs`.

## 4. Endpoints disponibles

Cada uno de estos prefijos expone `GET /`, `GET /{id}`, `POST /`,
`PUT /{id}` y `DELETE /{id}`:

| Prefijo | Entidad |
|---|---|
| `/roles` | Roles |
| `/usuarios` | Usuarios |
| `/ubicaciones` | Ubicaciones |
| `/tipos-sensor` | Tipos de sensor (catálogo ACS712, etc.) |
| `/unidades-medida` | Unidades de medida |
| `/tipos-umbral` | Tipos de umbral de alerta |
| `/dispositivos` | Dispositivos ESP32 |
| `/sensores` | Sensores físicos instalados |
| `/componentes` | Componentes eléctricos monitoreados |
| `/mediciones` | Mediciones de corriente/voltaje/potencia |
| `/umbrales` | Umbrales configurados por componente |
| `/alertas` | Alertas generadas |
| `/reportes` | Reportes PDF generados |
| `/reporte-detalle/{id_reporte}/{id_medicion}` | Relación reporte↔mediciones (PK compuesta) |

## 5. Conexión con el ESP32 (Parte 2)

El sketch del ESP32 envía cada medición así:

```
POST /mediciones
Content-Type: application/json

{
  "id_componente": 1,
  "corriente_a": 1.24,
  "voltaje_v": 120.0,
  "potencia_w": 148.8,
  "energia_kwh": 0.000206
}
```

Solo reemplaza `API_URL` en `sketch.ino` por la URL pública donde
despliegues esta API (por ejemplo con Render, Railway o un túnel
como ngrok si la corres localmente).

## 6. Ejemplo rápido con curl

```bash
# Crear una medición
curl -X POST http://127.0.0.1:8000/mediciones \
  -H "Content-Type: application/json" \
  -d '{"id_componente":1,"corriente_a":1.2,"voltaje_v":120,"potencia_w":144,"energia_kwh":0.012}'

# Listar mediciones
curl http://127.0.0.1:8000/mediciones
```
