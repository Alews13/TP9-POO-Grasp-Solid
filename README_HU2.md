# SmartTicket - HU2: Procesamiento de pago y emisión

Implementación incremental sobre **SmartTicket HU1**. No reemplaza `smartticket.db`.

## Endpoint principal

`POST /pagos/iniciar-pago`

```json
{
  "cliente_id": 1,
  "evento_id": 1,
  "sector_id": 1,
  "cantidad": 2,
  "total_cotizado": "24000.00",
  "tarjeta_prueba": "APROBADA"
}
```

Para simular rechazo, enviar `"tarjeta_prueba": "RECHAZADA"`.

La pasarela **es simulada**. Nunca enviar números reales de tarjeta, CVV ni datos bancarios. `entrada_ids` es un campo opcional: si se proporcionan los IDs exactos de las entradas seleccionadas, todos deben seguir `Disponible`; si se omite, se toman las primeras N disponibles del evento y sector. HU1 no reserva ni asigna IDs, por eso el modo sin `entrada_ids` es el flujo normal.

## Respuestas

- `200`: venta `Pagada` y entradas `Emitida` con `codigo_qr`.
- `402`: `Pago denegado` (no se registra venta, no se emiten entradas).
- `409`: `Los lugares seleccionados ya no se encuentran disponibles` (antes de llamar a la pasarela).
- `409`: `Cotización desactualizada` (si el importe recibido difiere del precio actual).
- `404`: cliente o precio no encontrado.
- `400`: cantidad o selección de entradas inválida.

Para obtener un `cliente_id`, se agregó `POST /clientes/`, además de `GET /clientes/` y `GET /clientes/{cliente_id}`.

## Responsabilidades

- `routers/pago.py`: traducción HTTP, sin reglas de negocio.
- `services/pago.py`: valida cliente, cantidad, cotización y stock; orquesta pasarela y emisión.
- `repositories/pago.py`: consultas y escrituras SQLAlchemy; ofrece contrato `PagoRepository`.
- `services/pasarela_pago.py`: interfaz `PasarelaPago` y pasarela simulada inyectable.
- `dependencies.py`: composición de dependencias con FastAPI `Depends`.
- `models/detalle_venta.py`: relación venta-entrada; garantiza que una entrada pertenezca como máximo a una venta y almacena su precio en centavos.

La operación usa `BEGIN IMMEDIATE` en SQLite antes de comprobar disponibilidad, y confirma la transacción después de emitir entradas y registrar la venta. Esta estrategia es adecuada para **una simulación local con SQLite**. Para una pasarela de pago real se necesitaría un diseño con reservas temporales, idempotencia y reconciliación de cobros; no se deben mantener bloqueos de base de datos durante llamadas de red lentas.

Se conserva `Venta.total` como `Float` para compatibilidad con la base existente de HU1. Los importes exactos se calculan en centavos enteros, se almacenan en `DetalleVenta.precio_centavos` y se devuelven como `Decimal` en la API.

## Archivos que reemplazan existentes

- `smartticket/main.py`
- `smartticket/dependencies.py`
- `smartticket/models/__init__.py`
- `smartticket/schemas/__init__.py`
- `smartticket/services/errors.py`
- `smartticket/routers/pago.py`

## Archivos nuevos

- `smartticket/models/detalle_venta.py`
- `smartticket/schemas/pago.py`
- `smartticket/schemas/cliente.py`
- `smartticket/services/pago.py`
- `smartticket/services/pasarela_pago.py`
- `smartticket/services/cliente.py`
- `smartticket/repositories/pago.py`
- `smartticket/routers/cliente.py`
- `smartticket/tests/test_hu2.py`
- `smartticket/README_HU2.md`
