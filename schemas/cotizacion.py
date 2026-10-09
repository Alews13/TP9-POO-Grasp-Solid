from decimal import Decimal
from pydantic import BaseModel, Field


class CotizacionRequest(BaseModel):
    evento_id: int = Field(gt=0, examples=[1])
    sector_id: int = Field(gt=0, examples=[1])
    # No poner gt=0: la HU exige que el SERVICIO rechace 0 y negativos con HTTP 400.
    cantidad: int = Field(examples=[2])


class CotizacionResponse(BaseModel):
    evento_id: int
    sector_id: int
    cantidad: int
    precio_unitario: Decimal = Field(description="Pesos exactos, serializados como cadena decimal")
    subtotal: Decimal = Field(description="Pesos exactos, serializados como cadena decimal")
    total: Decimal = Field(description="Total sin cargos adicionales, no previstos en la HU")
