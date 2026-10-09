from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import get_pago_service
from schemas.pago import PagoRequest, PagoResponse
from services.errors import (
    CantidadInvalidaError,
    CotizacionDesactualizadaError,
    DatosInvalidosError,
    EntradasNoDisponiblesError,
    PagoDenegadoError,
    PrecioNoConfiguradoError,
    RecursoNoEncontradoError,
)
from services.pago import PagoService

router = APIRouter(prefix="/pagos", tags=["Pagos"])


@router.post(
    "/iniciar-pago",
    response_model=PagoResponse,
    status_code=status.HTTP_200_OK,
    summary="Procesar pago y emitir entradas (HU2)",
    description=(
        "Revalida la cotización y disponibilidad antes de consultar una pasarela "
        "simulada. Si se aprueba, crea una venta Pagada y emite las entradas con QR."
    ),
    responses={
        400: {"description": "Cantidad o selección inválida"},
        402: {"description": "Pago denegado por la pasarela simulada"},
        404: {"description": "Cliente o precio no encontrado"},
        409: {"description": "Entradas no disponibles o cotización desactualizada"},
    },
)
def iniciar_pago(
    solicitud: PagoRequest,
    servicio: PagoService = Depends(get_pago_service),
):
    try:
        return servicio.iniciar_pago(solicitud)
    except (CantidadInvalidaError, DatosInvalidosError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PagoDenegadoError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except (EntradasNoDisponiblesError, CotizacionDesactualizadaError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RecursoNoEncontradoError, PrecioNoConfiguradoError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
