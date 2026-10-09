from datetime import datetime, timezone
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime: ...


class RelojSistema:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)
