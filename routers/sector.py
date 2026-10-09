from fastapi import APIRouter, Depends, HTTPException, status
from dependencies import get_sector_service
from schemas.sector import SectorCreate, SectorResponse
from services.catalogo import SectorService
from services.errors import RecursoNoEncontradoError

router = APIRouter(prefix="/sectores", tags=["Sectores"])


@router.post("/", response_model=SectorResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear sector", description="Asocia un sector con capacidad física a un lugar.")
def crear_sector(datos: SectorCreate, servicio: SectorService = Depends(get_sector_service)):
    try:
        return servicio.crear(datos)
    except RecursoNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/", response_model=list[SectorResponse], summary="Listar sectores")
def listar_sectores(servicio: SectorService = Depends(get_sector_service)):
    return servicio.listar()


@router.get("/{sector_id}", response_model=SectorResponse, summary="Buscar sector por ID")
def obtener_sector(sector_id: int, servicio: SectorService = Depends(get_sector_service)):
    try:
        return servicio.obtener(sector_id)
    except RecursoNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
