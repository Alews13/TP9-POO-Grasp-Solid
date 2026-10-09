from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import get_acceso_service
from schemas.acceso import AccesoRequest, AccesoResponse
from services.acceso import AccesoService
from services.errors import (
    EntradaYaUtilizadaError,
    EventoFueraDeFechaError,
    TicketInvalidoError,
    TicketNoEmitidoError,
)

router = APIRouter(prefix="/acceso", tags=["Control de acceso"])


@router.post(
    "/validar",
    response_model=AccesoResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar QR e ingresar al evento (HU3)",
    description=(
        "Busca el QR, verifica que la entrada esté Emitida, pagada y sea del "
        "evento del día. Marca la entrada Utilizada y registra la hora exacta "
        "en UTC. No admite dos ingresos con el mismo QR."
    ),
    responses={
        403: {"description": "Entrada no emitida, sin pago o fuera de fecha"},
        404: {"description": "Ticket Inválido o Inexistente"},
        409: {"description": "Entrada ya utilizada"},
    },
)
def validar_acceso(
    solicitud: AccesoRequest,
    servicio: AccesoService = Depends(get_acceso_service),
) -> AccesoResponse:
    try:
        return servicio.validar_acceso(solicitud)
    except TicketInvalidoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EntradaYaUtilizadaError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (TicketNoEmitidoError, EventoFueraDeFechaError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
