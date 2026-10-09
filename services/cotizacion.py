from decimal import Decimal
from repositories.cotizacion import CotizacionRepository
from schemas.cotizacion import CotizacionRequest, CotizacionResponse
from services.errors import (
    CantidadInvalidaError,
    CapacidadInsuficienteError,
    PrecioNoConfiguradoError,
)


def _a_pesos(centavos: int) -> Decimal:
    return (Decimal(centavos) / Decimal(100)).quantize(Decimal("0.01"))


class CotizacionService:
    def __init__(self, repositorio: CotizacionRepository):
        self.repositorio = repositorio

    def cotizar(self, solicitud: CotizacionRequest) -> CotizacionResponse:
        # Validar antes de consultar la base de datos.
        if solicitud.cantidad <= 0:
            raise CantidadInvalidaError("Cantidad inválida")

        precio_centavos = self.repositorio.obtener_precio_centavos(
            solicitud.evento_id, solicitud.sector_id
        )
        if precio_centavos is None:
            raise PrecioNoConfiguradoError("Evento, sector o precio no encontrado")

        disponibles = self.repositorio.contar_disponibles(
            solicitud.evento_id, solicitud.sector_id
        )
        if disponibles < solicitud.cantidad:
            raise CapacidadInsuficienteError("Capacidad insuficiente")

        subtotal_centavos = precio_centavos * solicitud.cantidad
        # Decimal + centavos enteros evitan errores de precisión con dinero.
        return CotizacionResponse(
            evento_id=solicitud.evento_id,
            sector_id=solicitud.sector_id,
            cantidad=solicitud.cantidad,
            precio_unitario=_a_pesos(precio_centavos),
            subtotal=_a_pesos(subtotal_centavos),
            total=_a_pesos(subtotal_centavos),
        )
