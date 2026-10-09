from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import get_cliente_service
from schemas.cliente import ClienteCreate, ClienteResponse
from services.cliente import ClienteService
from services.errors import DatosInvalidosError, RecursoNoEncontradoError

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post(
    "/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
    description="Registra un cliente para asociarle futuras ventas.",
)
def crear_cliente(datos: ClienteCreate, servicio: ClienteService = Depends(get_cliente_service)):
    try:
        return servicio.crear(datos)
    except DatosInvalidosError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=list[ClienteResponse], summary="Listar clientes")
def listar_clientes(servicio: ClienteService = Depends(get_cliente_service)):
    return servicio.listar()


@router.get("/{cliente_id}", response_model=ClienteResponse, summary="Obtener cliente")
def obtener_cliente(cliente_id: int, servicio: ClienteService = Depends(get_cliente_service)):
    try:
        return servicio.obtener(cliente_id)
    except RecursoNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
