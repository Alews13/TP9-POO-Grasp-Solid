from decimal import Decimal

from repositories.pago import PagoRepository
from schemas.pago import EntradaEmitidaResponse, PagoRequest, PagoResponse
from services.errors import (
    CantidadInvalidaError,
    CotizacionDesactualizadaError,
    DatosInvalidosError,
    EntradasNoDisponiblesError,
    PagoDenegadoError,
    PrecioNoConfiguradoError,
    RecursoNoEncontradoError,
)
from services.pasarela_pago import PasarelaPago


class PagoService:
    def __init__(self, repositorio: PagoRepository, pasarela: PasarelaPago):
        self.repositorio = repositorio
        self.pasarela = pasarela

    def iniciar_pago(self, solicitud: PagoRequest) -> PagoResponse:
        if solicitud.cantidad <= 0:
            raise CantidadInvalidaError("Cantidad inválida")
        if solicitud.entrada_ids is not None:
            ids = solicitud.entrada_ids
            if len(ids) != solicitud.cantidad or len(set(ids)) != len(ids):
                raise DatosInvalidosError("La selección de entradas es inválida")

        try:
            # Primero se obtiene el bloqueo; ninguna otra venta podrá adelantarse
            # entre la consulta de disponibilidad y la emisión en SQLite.
            self.repositorio.comenzar_transaccion()

            if not self.repositorio.cliente_existe(solicitud.cliente_id):
                raise RecursoNoEncontradoError("Cliente no encontrado")

            precio_centavos = self.repositorio.obtener_precio_centavos(
                solicitud.evento_id, solicitud.sector_id
            )
            if precio_centavos is None:
                raise PrecioNoConfiguradoError("Evento, sector o precio no encontrado")

            total_centavos = precio_centavos * solicitud.cantidad
            total_pesos = (Decimal(total_centavos) / Decimal(100)).quantize(
                Decimal("0.01")
            )
            if solicitud.total_cotizado != total_pesos:
                raise CotizacionDesactualizadaError("Cotización desactualizada")

            entradas_ids = self.repositorio.buscar_disponibles(
                solicitud.evento_id,
                solicitud.sector_id,
                solicitud.cantidad,
                solicitud.entrada_ids,
            )
            if len(entradas_ids) != solicitud.cantidad:
                raise EntradasNoDisponiblesError(
                    "Los lugares seleccionados ya no se encuentran disponibles"
                )

            # La pasarela se consulta SOLAMENTE si las entradas siguen disponibles.
            if not self.pasarela.procesar(solicitud.tarjeta_prueba, total_centavos):
                raise PagoDenegadoError("Pago denegado")

            venta_id, entradas = self.repositorio.registrar_venta_y_emitir(
                solicitud.cliente_id, entradas_ids, precio_centavos
            )
            self.repositorio.confirmar()
            return PagoResponse(
                venta_id=venta_id,
                estado="Pagada",
                total=total_pesos,
                entradas=[
                    EntradaEmitidaResponse(id=id_, codigo_qr=qr, estado="Emitida")
                    for id_, qr in entradas
                ],
            )
        except Exception:
            # Rechazo, stock insuficiente o error de DB: no dejar ventas parciales.
            self.repositorio.revertir()
            raise
