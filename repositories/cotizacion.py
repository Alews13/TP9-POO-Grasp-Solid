from typing import Protocol
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Entrada, Evento, PrecioSectorEvento, Sector


class CotizacionRepository(Protocol):
    """Abstracción para no acoplar el servicio a SQLAlchemy (DIP)."""

    def obtener_precio_centavos(self, evento_id: int, sector_id: int) -> int | None: ...

    def contar_disponibles(self, evento_id: int, sector_id: int) -> int: ...


class SQLAlchemyCotizacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener_precio_centavos(self, evento_id: int, sector_id: int) -> int | None:
        # Comprueba también que el sector pertenece al lugar del evento.
        stmt = (
            select(PrecioSectorEvento.precio_centavos)
            .join(Evento, Evento.id == PrecioSectorEvento.evento_id)
            .join(Sector, Sector.id == PrecioSectorEvento.sector_id)
            .where(
                PrecioSectorEvento.evento_id == evento_id,
                PrecioSectorEvento.sector_id == sector_id,
                Evento.lugar_id == Sector.lugar_id,
            )
        )
        return self.db.scalar(stmt)

    def contar_disponibles(self, evento_id: int, sector_id: int) -> int:
        stmt = select(func.count(Entrada.id)).where(
            Entrada.evento_id == evento_id,
            Entrada.sector_id == sector_id,
            Entrada.estado == "Disponible",
        )
        return self.db.scalar(stmt) or 0
