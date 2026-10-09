from typing import Protocol


class PasarelaPago(Protocol):
    """Abstracción intercambiable por una pasarela externa (DIP)."""

    def procesar(self, tarjeta_prueba: str, importe_centavos: int) -> bool: ...


class PasarelaPagoSimulada:
    """Aprobación/rechazo determinista, sin tarjetas ni cargos reales."""

    def procesar(self, tarjeta_prueba: str, importe_centavos: int) -> bool:
        return tarjeta_prueba == "APROBADA"
