from pydantic import BaseModel, ConfigDict, Field


class SectorCreate(BaseModel):
    nombre: str
    capacidad_maxima: int = Field(gt=0, description="Capacidad física máxima")
    lugar_id: int = Field(gt=0)


class SectorResponse(SectorCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
