from typing import Protocol

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from models import Cliente, DetalleVenta, Entrada, Evento, PrecioSectorEvento, Sector, Venta
from services.errors import EntradasNoDisponiblesError


class PagoRepository(Protocol):
    """Contrato de persistencia utilizado por PagoService."""

    def comenzar_transaccion(self) -> None: ...
    def cliente_existe(self, cliente_id: int) -> bool: ...
    def obtener_precio_centavos(self, evento_id: int, sector_id: int) -> int | None: ...
    def buscar_disponibles(
        self, evento_id: int, sector_id: int, cantidad: int,
        entrada_ids: list[int] | None,
    ) -> list[int]: ...
    def registrar_venta_y_emitir(
        self, cliente_id: int, entrada_ids: list[int], precio_centavos: int,
    ) -> tuple[int, list[tuple[int, str]]]: ...
    def confirmar(self) -> None: ...
    def revertir(self) -> None: ...


class SQLAlchemyPagoRepository:
    def __init__(self, db: Session):
        self.db = db

    def comenzar_transaccion(self) -> None:
        # SQLite no implementa SELECT ... FOR UPDATE.
        # BEGIN IMMEDIATE serializa escrituras ANTES de comprobar disponibilidad.
        # Mantener esta transacción hasta terminar el pago SIMULADO.
        self.db.execute(text("BEGIN IMMEDIATE"))

    def cliente_existe(self, cliente_id: int) -> bool:
        return self.db.get(Cliente, cliente_id) is not None

    def obtener_precio_centavos(self, evento_id: int, sector_id: int) -> int | None:
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

    def buscar_disponibles(
        self, evento_id: int, sector_id: int, cantidad: int,
        entrada_ids: list[int] | None,
    ) -> list[int]:
        stmt = select(Entrada.id).where(
            Entrada.evento_id == evento_id,
            Entrada.sector_id == sector_id,
            Entrada.estado == "Disponible",
        )
        if entrada_ids is not None:
            stmt = stmt.where(Entrada.id.in_(entrada_ids))
        else:
            stmt = stmt.limit(cantidad)
        return list(self.db.scalars(stmt.order_by(Entrada.id)).all())

    def registrar_venta_y_emitir(
        self, cliente_id: int, entrada_ids: list[int], precio_centavos: int,
    ) -> tuple[int, list[tuple[int, str]]]:
        # Conservamos la columna Float legacy de Venta para no romper la DB de HU1.
        # El valor monetario exacto queda en centavos por cada DetalleVenta.
        venta = Venta(
            cliente_id=cliente_id,
            estado="Pagada",
            total=(precio_centavos * len(entrada_ids)) / 100,
        )
        self.db.add(venta)
        self.db.flush()

        cambio = self.db.execute(
            update(Entrada)
            .where(Entrada.id.in_(entrada_ids), Entrada.estado == "Disponible")
            .values(estado="Emitida")
        )
        if cambio.rowcount != len(entrada_ids):
            raise EntradasNoDisponiblesError(
                "Los lugares seleccionados ya no se encuentran disponibles"
            )

        self.db.add_all([
            DetalleVenta(
                venta_id=venta.id,
                entrada_id=entrada_id,
                precio_centavos=precio_centavos,
            )
            for entrada_id in entrada_ids
        ])
        entradas = self.db.execute(
            select(Entrada.id, Entrada.codigo_qr)
            .where(Entrada.id.in_(entrada_ids))
            .order_by(Entrada.id)
        ).all()
        return venta.id, [(id_, qr) for id_, qr in entradas]

    def confirmar(self) -> None:
        self.db.commit()

    def revertir(self) -> None:
        self.db.rollback()
