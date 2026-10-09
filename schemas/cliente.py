from pydantic import BaseModel, ConfigDict, Field


class ClienteCreate(BaseModel):
    nombre: str = Field(min_length=1)
    email: str = Field(min_length=3)


class ClienteResponse(ClienteCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
