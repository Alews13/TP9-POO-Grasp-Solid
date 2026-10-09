from fastapi import APIRouter, Depends, HTTPException, status
from dependencies import get_cotizacion_service
from schemas.cotizacion import CotizacionRequest, CotizacionResponse
from services.cotizacion import CotizacionService
from services.errors import (
    CantidadInvalidaError,
    CapacidadInsuficienteError,
    PrecioNoConfiguradoError,
)

router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


@router.post(
    "/cotizar",
    response_model=CotizacionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cotizar entradas (HU1)",
    description="Calcula el precio exacto si hay entradas disponibles; no reserva ni emite.",
    responses={
        400: {"description": "Cantidad inválida o capacidad insuficiente"},
        404: {"description": "Evento, sector o precio no encontrado"},
    },
)
def cotizar(
    solicitud: CotizacionRequest,
    servicio: CotizacionService = Depends(get_cotizacion_service),
):
    try:
        return servicio.cotizar(solicitud)
    except (CantidadInvalidaError, CapacidadInsuficienteError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrecioNoConfiguradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
