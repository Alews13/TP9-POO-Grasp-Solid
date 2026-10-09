from datetime import timezone
from zoneinfo import ZoneInfo

from repositories.acceso import AccesoRepository
from schemas.acceso import AccesoRequest, AccesoResponse
from services.errors import (
    EntradaYaUtilizadaError,
    EventoFueraDeFechaError,
    TicketInvalidoError,
    TicketNoEmitidoError,
)
from services.reloj import Reloj


class AccesoService:
    """Aplica las reglas de ingreso y coordina una única transacción."""

    def __init__(
        self,
        repositorio: AccesoRepository,
        reloj: Reloj,
        zona_evento: ZoneInfo,
    ):
        self.repositorio = repositorio
        self.reloj = reloj
        self.zona_evento = zona_evento

    def validar_acceso(self, solicitud: AccesoRequest) -> AccesoResponse:
        try:
            self.repositorio.comenzar_transaccion()
            ticket = self.repositorio.buscar_por_qr(solicitud.codigo_qr)

            if ticket is None:
                raise TicketInvalidoError("Ticket Inválido o Inexistente")

            # La hora de ingreso nunca se sobreescribe.
            if ticket.estado == "Utilizada" or ticket.hora_ingreso is not None:
                raise EntradaYaUtilizadaError("Entrada ya utilizada")

            # Una entrada Emitida sin venta Pagada tampoco habilita el ingreso.
            if ticket.estado != "Emitida" or ticket.estado_venta != "Pagada":
                raise TicketNoEmitidoError("Ticket no emitido / Falta de pago")

            ahora = self.reloj.ahora()
            if ahora.tzinfo is None or ahora.utcoffset() is None:
                raise ValueError("El reloj debe devolver un instante con zona horaria")
            ahora_utc = ahora.astimezone(timezone.utc)

            # Evento.fecha se guarda como hora LOCAL del evento (sin zona).
            if ticket.fecha_evento.date() != ahora_utc.astimezone(self.zona_evento).date():
                raise EventoFueraDeFechaError("El ticket no corresponde al evento del día")

            # Guardamos UTC sin tzinfo porque SQLite DateTime no conserva el offset.
            # La API devuelve el mismo instante en UTC con tzinfo explícito.
            if not self.repositorio.marcar_utilizada(
                ticket.entrada_id, ahora_utc.replace(tzinfo=None)
            ):
                raise EntradaYaUtilizadaError("Entrada ya utilizada")

            self.repositorio.confirmar()
            return AccesoResponse(
                mensaje="Acceso Permitido",
                entrada_id=ticket.entrada_id,
                evento_id=ticket.evento_id,
                estado="Utilizada",
                hora_ingreso=ahora_utc,
            )
        except Exception:
            self.repositorio.revertir()
            raise
