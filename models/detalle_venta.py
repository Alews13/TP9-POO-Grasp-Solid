from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, UniqueConstraint
from database import Base


class DetalleVenta(Base):
    """Asocia una entrada a una única venta y conserva su precio exacto."""

    __tablename__ = "detalles_venta"
    __table_args__ = (
        UniqueConstraint("entrada_id", name="uq_entrada_vendida_una_vez"),
        CheckConstraint("precio_centavos >= 0", name="ck_detalle_precio_no_negativo"),
    )

    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    entrada_id = Column(Integer, ForeignKey("entradas.id"), nullable=False)
    precio_centavos = Column(Integer, nullable=False)
