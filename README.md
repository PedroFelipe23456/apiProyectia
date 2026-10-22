# API Taller 1 — PowerMonitor IoT

API REST (FastAPI + SQLAlchemy) y aplicación web para:

- **Energía**: medir voltaje, corriente y potencia con un ESP32 + ACS712 y guardarlo en PostgreSQL.
- **Motor**: controlar la velocidad y dirección de un motor DC (ESP32 + L298N) desde la web.
- **Catálogos**: CRUD de roles, usuarios, ubicaciones, sensores, componentes, umbrales, alertas y reportes.
- **Visión**: detección con YOLOv8 (focos encendidos/apagados y personas).
- **WhatsApp**: chatbot de consultas (Twilio + Ollama).

## Estructura

```
app/
  main.py                  # crea la app y registra cada módulo
  core/
    database.py            # conexión a PostgreSQL (lee DATABASE_URL de .env)
    crud_router.py         # CRUDRouter genérico: arma las 5 rutas REST de una tabla
  db/
    models.py              # entidades ORM (una clase por tabla)
    schemas.py             # validación Pydantic (Create / Read)
    repository.py          # BaseRepository genérico + un repositorio por entidad
  modules/
    energia/router.py      # /mediciones
    motor/router.py        # /motor
    catalogos/router.py    # /roles, /usuarios, ... (usa CRUDRouter)
    catalogos/reporte_detalle.py  # /reporte-detalle (llave primaria compuesta)
    vision/router.py       # /vision/detectar  (+ best.pt)
    whatsapp/router.py     # /webhook/whatsapp
  static/                  # aplicación web
    index.html             # shell: acceso, navegación y las 3 vistas
    css/styles.css         # sistema de diseño (modo oscuro y claro, responsive)
    js/api.js              # fetch, formato de números, aviso "despertando servidor"
    js/app.js              # sesión, navegación por módulos, tema, estado del ESP32
    js/energia.js          # módulo Energía: KPIs, 5 gráficos y tabla
    js/motor.js            # módulo Motor: slider, dirección y DETENER
    js/prediccion.js       # módulo Predicción
exportar.py                # exporta las mediciones a datos_sensores.csv
```

## 1. Instalación (Windows, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> `ultralytics` (YOLO) es pesado. Si solo vas a usar energía y motor puedes
> omitirlo: el módulo de visión carga el modelo la primera vez que se usa y
> el resto de la API funciona sin él.

## 2. Base de datos

1. Copia `.env.example` a `.env`.
2. Pon en `DATABASE_URL` la cadena de tu PostgreSQL (la misma donde corriste `taller1_basedatos.sql`).

`.env` **no se sube a GitHub** (está en `.gitignore`). La API no crea las tablas.

## 3. Ejecutar

```powershell
uvicorn app.main:app --reload
```

- Aplicación web: http://127.0.0.1:8000
- Documentación (Swagger): http://127.0.0.1:8000/docs

## 4. Endpoints

### Energía
| Método | Ruta | Quién | Qué hace |
|---|---|---|---|
| POST | `/mediciones/` | ESP32 | Guarda una medición |
| GET | `/mediciones/?limit=20` | Web, LCD | Historial, más reciente primero |
| GET | `/mediciones/resumen` | Web | Promedios, máximo, mínimo y energía total |
| GET | `/mediciones/vivo?n=120` | Web | Lecturas en tiempo real (memoria, ~1 por segundo) |
| GET | `/mediciones/menu` | Web | Todas las opciones del menú del teclado en un JSON |

### Menú del teclado HX-543
Cada opción responde `{"resultado": "..."}` con un texto de máximo 16 caracteres para el LCD.

| Tecla | Ruta | Ejemplo |
|---|---|---|
| 2 | `/mediciones/ultimo` | `V:5.7V P:1.20W` |
| 3 | `/mediciones/promedio-24h` | `Prom: 1.34 W` |
| 4 | `/mediciones/maxmin-24h` | `Mx:1.7 Mn:1.0W` |
| 5 | `/mediciones/promedio-hora` | `Prom H: 1.34 W` |
| 6 | `/mediciones/registros-24h` | `Total: 30 regs` |
| 9 | `/mediciones/desviacion` | `SD: 0.19 W` |

Las opciones 1, 7, 8, 0 y A se resuelven en el ESP32 sin consultar la API.

### Motor
| Método | Ruta | Quién | Qué hace |
|---|---|---|---|
| GET | `/motor/?v=5.8&i=230&p=1.33` | ESP32 (cada 1 s) | Devuelve `{"velocidad", "direccion"}` y guarda la lectura en vivo |
| PUT | `/motor/` | Web | Cambia velocidad (0-100) y dirección (`adelante`, `atras`, `stop`) |
| GET | `/motor/estado` | Web | Estado + ESP32 conectado + lectura en vivo |

El estado del motor está en memoria: si el servidor reinicia vuelve a `stop`.

### Catálogos
Cada prefijo expone `GET /`, `GET /{id}`, `POST /`, `PUT /{id}` y `DELETE /{id}`:
`/roles`, `/usuarios`, `/ubicaciones`, `/tipos-sensor`, `/unidades-medida`, `/tipos-umbral`,
`/dispositivos`, `/sensores`, `/componentes`, `/umbrales`, `/alertas`, `/reportes`
y `/reporte-detalle/{id_reporte}/{id_medicion}`.

## 5. Conexión con el ESP32

En el sketch:

```cpp
const char* API_URL       = "https://TU-SERVICIO.onrender.com/mediciones/";
const char* API_MOTOR_URL = "https://TU-SERVICIO.onrender.com/motor/";
```

Las dos terminan en `/`: el ESP32 no sigue redirecciones.

## 6. Despliegue en Render

- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Variable de entorno: `DATABASE_URL` (en Render → Environment, no en el código).
