from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, UniqueConstraint
from database import Base


class PrecioSectorEvento(Base):
    """Precio específico de un sector para un evento (en centavos)."""

    __tablename__ = "precios_sector_evento"
    __table_args__ = (
        UniqueConstraint("evento_id", "sector_id", name="uq_precio_evento_sector"),
        CheckConstraint("precio_centavos >= 0", name="ck_precio_no_negativo"),
    )

    id = Column(Integer, primary_key=True)
    evento_id = Column(Integer, ForeignKey("eventos.id"), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=False)
    precio_centavos = Column(Integer, nullable=False)
