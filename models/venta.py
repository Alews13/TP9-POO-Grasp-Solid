from sqlalchemy import Column, Float, ForeignKey, Integer, String
from database import Base


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    estado = Column(String, nullable=False, default="Pendiente")
    total = Column(Float, nullable=False, default=0)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
