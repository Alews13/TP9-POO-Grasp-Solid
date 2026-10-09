from sqlalchemy import Column, Integer, String
from database import Base


class Lugar(Base):
    __tablename__ = "lugares"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
