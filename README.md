# SmartTicket | Historia de Usuario 1

Backend con **FastAPI + SQLAlchemy + SQLite**, con capas separadas para cotización.

## Instalación (Windows)

Abrir una terminal dentro de `smartticket/`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecutar

```powershell
python -m uvicorn main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Crear datos desde Swagger

1. `POST /lugares/`:

   ```json
   {"nombre": "Estadio", "direccion": "Buenos Aires"}
   ```

2. `POST /sectores/` dos veces (reemplazar `lugar_id` por el ID obtenido):

   ```json
   {"nombre": "Platea", "capacidad_maxima": 2, "lugar_id": 1}
   ```

   ```json
   {"nombre": "VIP", "capacidad_maxima": 1, "lugar_id": 1}
   ```

3. `POST /eventos/` (reemplazar IDs por los que devuelve Swagger):

   ```json
   {
     "nombre": "Rock Fest",
     "fecha": "2026-12-15T21:00:00",
     "lugar_id": 1,
     "precios": [
       {"sector_id": 1, "precio_centavos": 1200000},
       {"sector_id": 2, "precio_centavos": 2000000}
     ]
   }
   ```

   Crear el evento genera **2 entradas Platea y 1 VIP** en estado `Disponible`.

4. `POST /cotizaciones/cotizar`:

   ```json
   {"evento_id": 1, "sector_id": 1, "cantidad": 2}
   ```

   HTTP 200:

   ```json
   {
     "evento_id": 1,
     "sector_id": 1,
     "cantidad": 2,
     "precio_unitario": "12000.00",
     "subtotal": "24000.00",
     "total": "24000.00"
   }
   ```

   Los importes se devuelven como **cadenas decimales exactas** (Pydantic `Decimal`), no `float`.

5. Probar errores:

   - `cantidad: 0` o negativa → HTTP 400 `Cantidad inválida`.
   - `sector_id` del VIP y `cantidad: 3` → HTTP 400 `Capacidad insuficiente`.

**Importante:** los IDs de ejemplo pueden ser distintos en tu base local.

## Cargar un ejemplo automáticamente (alternativa a Swagger)

Con el servidor detenido o desde otra terminal, ejecutar desde la carpeta `smartticket/`:

```powershell
python -m scripts.cargar_demo
```

Imprime los IDs reales de Rock Fest, Platea y VIP. Si ya existe el evento demo, lo conserva sin cambiar entradas.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Arquitectura

- `routers/cotizacion.py`: traduce peticiones y errores a HTTP.
- `services/cotizacion.py`: validación de cantidad, stock y multiplicación (GRASP Experto, SRP).
- `repositories/cotizacion.py`: consultas SQLAlchemy; expone un `Protocol` para invertir dependencias (DIP).
- `dependencies.py`: inyecta el repositorio al servicio mediante FastAPI `Depends`.
- `models/precio_sector_evento.py`: precio propio por combinación evento/sector, expresado en centavos enteros.
- `services/catalogo.py`: permite crear sectores y eventos desde Swagger, generando las entradas al crear un evento.

Cotizar **no modifica entradas ni reserva stock**. HU2 debe volver a comprobar disponibilidad antes de procesar el pago. No se implementó pago ni validación de QR.

**Nota:** `create_all` crea tablas nuevas, pero no migra columnas de tablas existentes. Se mantienen las columnas de los modelos previos para que el proyecto pueda usar la base local anterior.
