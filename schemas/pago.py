from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


class PagoRequest(BaseModel):
    cliente_id: int = Field(gt=0, examples=[1])
    evento_id: int = Field(gt=0, examples=[1])
    sector_id: int = Field(gt=0, examples=[1])
    cantidad: int = Field(examples=[2])
    total_cotizado: Decimal = Field(
        ge=0,
        decimal_places=2,
        examples=["24000.00"],
        description="Total recibido en HU1, expresado en pesos",
    )
    tarjeta_prueba: Literal["APROBADA", "RECHAZADA"] = Field(
        examples=["APROBADA"],
        description="Solo simulación. No enviar número real de tarjeta ni CVV.",
    )
    entrada_ids: list[int] | None = Field(
        default=None,
        description=(
            "Opcional: IDs exactos elegidos previamente. Si se omite, "
            "se seleccionan N entradas disponibles del sector."
        ),
    )


class EntradaEmitidaResponse(BaseModel):
    id: int
    codigo_qr: str
    estado: Literal["Emitida"]


class PagoResponse(BaseModel):
    venta_id: int
    estado: Literal["Pagada"]
    total: Decimal = Field(description="Importe exacto en pesos")
    entradas: list[EntradaEmitidaResponse]
