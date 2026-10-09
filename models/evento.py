from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from database import Base


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    fecha = Column(DateTime, nullable=False)
    lugar_id = Column(Integer, ForeignKey("lugares.id"), nullable=False)
