from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PrecioSectorCreate(BaseModel):
    sector_id: int = Field(gt=0)
    precio_centavos: int = Field(ge=0, description="Precio en centavos; 12000 pesos = 1200000")


class EventoCreate(BaseModel):
    nombre: str
    fecha: datetime
    lugar_id: int = Field(gt=0)
    precios: list[PrecioSectorCreate] = Field(min_length=1)


class EventoResponse(BaseModel):
    id: int
    nombre: str
    fecha: datetime
    lugar_id: int
    model_config = ConfigDict(from_attributes=True)
