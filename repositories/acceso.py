from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from models import DetalleVenta, Entrada, Evento, Venta


@dataclass(frozen=True)
class DatosTicket:
    entrada_id: int
    evento_id: int
    estado: str
    hora_ingreso: datetime | None
    fecha_evento: datetime
    estado_venta: str | None


class AccesoRepository(Protocol):
    """Contrato de persistencia; el servicio no conoce SQLAlchemy."""

    def comenzar_transaccion(self) -> None: ...
    def buscar_por_qr(self, codigo_qr: str) -> DatosTicket | None: ...
    def marcar_utilizada(self, entrada_id: int, instante_utc: datetime) -> bool: ...
    def confirmar(self) -> None: ...
    def revertir(self) -> None: ...


class SQLAlchemyAccesoRepository:
    def __init__(self, db: Session):
        self.db = db

    def comenzar_transaccion(self) -> None:
        # SQLite no ofrece bloqueo de filas con SELECT FOR UPDATE.
        # BEGIN IMMEDIATE serializa escrituras desde antes de leer el estado.
        self.db.execute(text("BEGIN IMMEDIATE"))

    def buscar_por_qr(self, codigo_qr: str) -> DatosTicket | None:
        fila = self.db.execute(
            select(
                Entrada.id,
                Entrada.evento_id,
                Entrada.estado,
                Entrada.hora_ingreso,
                Evento.fecha,
                Venta.estado,
            )
            .join(Evento, Evento.id == Entrada.evento_id)
            .outerjoin(DetalleVenta, DetalleVenta.entrada_id == Entrada.id)
            .outerjoin(Venta, Venta.id == DetalleVenta.venta_id)
            .where(Entrada.codigo_qr == codigo_qr)
        ).one_or_none()
        if fila is None:
            return None
        return DatosTicket(
            entrada_id=fila[0],
            evento_id=fila[1],
            estado=fila[2],
            hora_ingreso=fila[3],
            fecha_evento=fila[4],
            estado_venta=fila[5],
        )

    def marcar_utilizada(self, entrada_id: int, instante_utc: datetime) -> bool:
        # La condición protege la hora original incluso ante un segundo escaneo.
        resultado = self.db.execute(
            update(Entrada)
            .where(
                Entrada.id == entrada_id,
                Entrada.estado == "Emitida",
                Entrada.hora_ingreso.is_(None),
            )
            .values(estado="Utilizada", hora_ingreso=instante_utc)
        )
        return resultado.rowcount == 1

    def confirmar(self) -> None:
        self.db.commit()

    def revertir(self) -> None:
        self.db.rollback()
