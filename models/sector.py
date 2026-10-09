from sqlalchemy import Column, ForeignKey, Integer, String
from database import Base


class Sector(Base):
    __tablename__ = "sectores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    capacidad_maxima = Column(Integer, nullable=False)
    lugar_id = Column(Integer, ForeignKey("lugares.id"), nullable=False)
