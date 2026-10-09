# SmartTicket - HU3: Control de acceso en puerta

Esta entrega contiene **solo archivos nuevos y modificados** respecto de HU2.
No reemplazar ni borrar `smartticket.db`.

## Endpoint

`POST /acceso/validar`

```json
{"codigo_qr": "CODIGO_DEVUELTO_EN_HU2"}
```

- `200`: `Acceso Permitido`, entrada `Utilizada`, `hora_ingreso` en UTC.
- `409`: `Entrada ya utilizada`, conserva `hora_ingreso` anterior.
- `404`: `Ticket Inválido o Inexistente`.
- `403`: `Ticket no emitido / Falta de pago`.
- `403`: `El ticket no corresponde al evento del día`.

## Notas de diseño

- `Evento.fecha` existente es fecha y hora **local del evento**, sin zona horaria.
- La zona predeterminada es `America/Argentina/Buenos_Aires` y puede configurarse
  con la variable de entorno `SMARTTICKET_TIMEZONE` (zona IANA). `tzdata` permite
  resolver estas zonas también en Windows.
- `Entrada.hora_ingreso` se persiste como fecha/hora **UTC sin tzinfo**, para
  mantener compatibilidad con la columna SQLite existente. La respuesta HTTP
  incluye el instante UTC con offset. No se requiere migración de la base.
- Una entrada `Emitida` debe estar asociada a una `Venta` `Pagada`.
- Se usa `BEGIN IMMEDIATE` y `UPDATE ... WHERE estado='Emitida' AND
  hora_ingreso IS NULL` para impedir un segundo ingreso y proteger la hora original.
- La comprobación de fecha es por **día calendario local**, no por horario de
  apertura. Si en el futuro se necesitan accesos durante la madrugada siguiente,
  deberá definirse explícitamente la ventana de acceso del evento.

## Separación de responsabilidades

- `routers/acceso.py`: capa HTTP, sin reglas de negocio.
- `services/acceso.py`: valida QR, estado, pago, fecha y coordina transacción.
- `repositories/acceso.py`: SQLAlchemy, consultas y actualización condicional.
- `services/reloj.py`: reloj inyectable, facilita pruebas reproducibles.
- `dependencies.py`: composición de repositorio, reloj y servicio con `Depends`.

## Archivos reemplazados

- `smartticket/main.py`
- `smartticket/dependencies.py`
- `smartticket/services/errors.py`
- `smartticket/requirements.txt`

## Archivos nuevos

- `smartticket/routers/acceso.py`
- `smartticket/schemas/acceso.py`
- `smartticket/services/acceso.py`
- `smartticket/services/reloj.py`
- `smartticket/repositories/acceso.py`
- `smartticket/tests/test_hu3.py`
- `smartticket/README_HU3.md`
