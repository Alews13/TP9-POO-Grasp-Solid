from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AccesoRequest(BaseModel):
    codigo_qr: str = Field(
        min_length=1,
        examples=["c0e6f786-67c2-48f3-9461-452c85845e30"],
        description="Código QR devuelto al pagar una entrada (HU2).",
    )


class AccesoResponse(BaseModel):
    mensaje: Literal["Acceso Permitido"]
    entrada_id: int
    evento_id: int
    estado: Literal["Utilizada"]
    hora_ingreso: datetime = Field(
        description="Instante exacto del ingreso en UTC (ISO 8601)."
    )
