from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from repositories.cotizacion import SQLAlchemyCotizacionRepository
from services.cotizacion import CotizacionService


def get_cotizacion_service(db: Session = Depends(get_db)) -> CotizacionService:
    repositorio = SQLAlchemyCotizacionRepository(db)
    return CotizacionService(repositorio)

from services.catalogo import EventoService, SectorService


def get_sector_service(db: Session = Depends(get_db)) -> SectorService:
    return SectorService(db)


def get_evento_service(db: Session = Depends(get_db)) -> EventoService:
    return EventoService(db)


# Inyección de dependencias para HU2.
from repositories.pago import PagoRepository, SQLAlchemyPagoRepository
from services.pago import PagoService
from services.pasarela_pago import PasarelaPago, PasarelaPagoSimulada
from services.cliente import ClienteService


def get_pago_repository(db: Session = Depends(get_db)) -> PagoRepository:
    return SQLAlchemyPagoRepository(db)


def get_pasarela_pago() -> PasarelaPago:
    return PasarelaPagoSimulada()


def get_pago_service(
    repositorio: PagoRepository = Depends(get_pago_repository),
    pasarela: PasarelaPago = Depends(get_pasarela_pago),
) -> PagoService:
    return PagoService(repositorio, pasarela)


def get_cliente_service(db: Session = Depends(get_db)) -> ClienteService:
    return ClienteService(db)


# Inyección de dependencias para HU3.
import os
from zoneinfo import ZoneInfo
from repositories.acceso import AccesoRepository, SQLAlchemyAccesoRepository
from services.acceso import AccesoService
from services.reloj import Reloj, RelojSistema


def get_acceso_repository(db: Session = Depends(get_db)) -> AccesoRepository:
    return SQLAlchemyAccesoRepository(db)


def get_reloj() -> Reloj:
    return RelojSistema()


def get_zona_evento() -> ZoneInfo:
    return ZoneInfo(os.getenv("SMARTTICKET_TIMEZONE", "America/Argentina/Buenos_Aires"))


def get_acceso_service(
    repositorio: AccesoRepository = Depends(get_acceso_repository),
    reloj: Reloj = Depends(get_reloj),
    zona_evento: ZoneInfo = Depends(get_zona_evento),
) -> AccesoService:
    return AccesoService(repositorio, reloj, zona_evento)
