from pydantic import BaseModel, ConfigDict


class LugarCreate(BaseModel):
    nombre: str
    direccion: str


class LugarResponse(LugarCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
