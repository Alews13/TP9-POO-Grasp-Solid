from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from database import Base


class Entrada(Base):
    __tablename__ = "entradas"

    id = Column(Integer, primary_key=True, index=True)
    codigo_qr = Column(String, unique=True, nullable=False)
    estado = Column(String, nullable=False, default="Disponible")
    hora_ingreso = Column(DateTime, nullable=True)
    evento_id = Column(Integer, ForeignKey("eventos.id"), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=False)
