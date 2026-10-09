from fastapi import APIRouter, Depends, HTTPException, status
from dependencies import get_evento_service
from schemas.evento import EventoCreate, EventoResponse
from services.catalogo import EventoService
from services.errors import DatosInvalidosError, RecursoNoEncontradoError

router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.post(
    "/", response_model=EventoResponse, status_code=status.HTTP_201_CREATED,
    summary="Crear evento con precios y entradas",
    description="Requiere un precio para cada sector del lugar. Genera entradas disponibles según su capacidad.",
    responses={400: {"description": "Precios o sectores inválidos"},
               404: {"description": "Lugar no encontrado"}},
)
def crear_evento(datos: EventoCreate, servicio: EventoService = Depends(get_evento_service)):
    try:
        return servicio.crear(datos)
    except RecursoNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatosInvalidosError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/", response_model=list[EventoResponse], summary="Listar eventos")
def listar_eventos(servicio: EventoService = Depends(get_evento_service)):
    return servicio.listar()


@router.get("/{evento_id}", response_model=EventoResponse, summary="Buscar evento por ID")
def obtener_evento(evento_id: int, servicio: EventoService = Depends(get_evento_service)):
    try:
        return servicio.obtener(evento_id)
    except RecursoNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
