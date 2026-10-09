from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Cliente
from schemas.cliente import ClienteCreate
from services.errors import DatosInvalidosError, RecursoNoEncontradoError


class ClienteService:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, datos: ClienteCreate) -> Cliente:
        cliente = Cliente(**datos.model_dump())
        self.db.add(cliente)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DatosInvalidosError("Ya existe un cliente con ese email") from exc
        self.db.refresh(cliente)
        return cliente

    def listar(self) -> list[Cliente]:
        return list(self.db.scalars(select(Cliente).order_by(Cliente.id)).all())

    def obtener(self, cliente_id: int) -> Cliente:
        cliente = self.db.get(Cliente, cliente_id)
        if cliente is None:
            raise RecursoNoEncontradoError("Cliente no encontrado")
        return cliente
