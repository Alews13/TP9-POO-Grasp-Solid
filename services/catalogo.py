from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Entrada, Evento, Lugar, PrecioSectorEvento, Sector
from schemas.evento import EventoCreate
from schemas.sector import SectorCreate
from services.errors import DatosInvalidosError, RecursoNoEncontradoError


class SectorService:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, datos: SectorCreate) -> Sector:
        if self.db.get(Lugar, datos.lugar_id) is None:
            raise RecursoNoEncontradoError("Lugar no encontrado")
        sector = Sector(**datos.model_dump())
        self.db.add(sector)
        self.db.commit()
        self.db.refresh(sector)
        return sector

    def listar(self) -> list[Sector]:
        return list(self.db.scalars(select(Sector)).all())

    def obtener(self, sector_id: int) -> Sector:
        sector = self.db.get(Sector, sector_id)
        if sector is None:
            raise RecursoNoEncontradoError("Sector no encontrado")
        return sector


class EventoService:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, datos: EventoCreate) -> Evento:
        if self.db.get(Lugar, datos.lugar_id) is None:
            raise RecursoNoEncontradoError("Lugar no encontrado")

        sectores = list(self.db.scalars(
            select(Sector).where(Sector.lugar_id == datos.lugar_id)
        ).all())
        if not sectores:
            raise DatosInvalidosError("El lugar debe tener sectores antes de crear el evento")

        sectores_del_lugar = {sector.id for sector in sectores}
        sectores_con_precio = [precio.sector_id for precio in datos.precios]
        if len(set(sectores_con_precio)) != len(sectores_con_precio):
            raise DatosInvalidosError("No puede repetirse el precio de un sector")
        if set(sectores_con_precio) != sectores_del_lugar:
            raise DatosInvalidosError("Debe fijar un precio para cada sector del lugar")

        try:
            evento = Evento(nombre=datos.nombre, fecha=datos.fecha, lugar_id=datos.lugar_id)
            self.db.add(evento)
            self.db.flush()  # Obtiene ID sin confirmar todavía la transacción.

            for precio in datos.precios:
                self.db.add(PrecioSectorEvento(
                    evento_id=evento.id,
                    sector_id=precio.sector_id,
                    precio_centavos=precio.precio_centavos,
                ))

            # Regla del dominio: las entradas PREEXISTEN y se crean al crear el evento.
            for sector in sectores:
                for _ in range(sector.capacidad_maxima):
                    self.db.add(Entrada(
                        evento_id=evento.id,
                        sector_id=sector.id,
                        codigo_qr=str(uuid4()),
                        estado="Disponible",
                    ))

            self.db.commit()
            self.db.refresh(evento)
            return evento
        except Exception:
            self.db.rollback()
            raise

    def listar(self) -> list[Evento]:
        return list(self.db.scalars(select(Evento)).all())

    def obtener(self, evento_id: int) -> Evento:
        evento = self.db.get(Evento, evento_id)
        if evento is None:
            raise RecursoNoEncontradoError("Evento no encontrado")
        return evento
