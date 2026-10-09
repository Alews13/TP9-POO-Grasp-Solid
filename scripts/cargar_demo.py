"""Carga Rock Fest con 2 Platea y 1 VIP para probar los escenarios HU1.
Ejecutar desde la raíz: python -m scripts.cargar_demo
"""
from datetime import datetime
from sqlalchemy import select

from database import Base, SessionLocal, engine
import models
from models import Evento, Lugar, Sector
from schemas.evento import EventoCreate, PrecioSectorCreate
from services.catalogo import EventoService

Base.metadata.create_all(bind=engine)


def main():
    with SessionLocal() as db:
        lugar = db.scalar(select(Lugar).where(Lugar.nombre == "Estadio Demo SmartTicket"))
        if lugar is None:
            lugar = Lugar(nombre="Estadio Demo SmartTicket", direccion="Buenos Aires")
            db.add(lugar)
            db.flush()

        def asegurar_sector(nombre: str, capacidad: int):
            sector = db.scalar(select(Sector).where(
                Sector.lugar_id == lugar.id, Sector.nombre == nombre
            ))
            if sector is None:
                sector = Sector(nombre=nombre, capacidad_maxima=capacidad, lugar_id=lugar.id)
                db.add(sector)
                db.flush()
            return sector

        platea = asegurar_sector("Platea", 2)
        vip = asegurar_sector("VIP", 1)
        db.commit()

        evento = db.scalar(select(Evento).where(
            Evento.nombre == "Rock Fest", Evento.lugar_id == lugar.id
        ))
        if evento is None:
            evento = EventoService(db).crear(EventoCreate(
                nombre="Rock Fest",
                fecha=datetime(2026, 12, 15, 21, 0),
                lugar_id=lugar.id,
                precios=[
                    PrecioSectorCreate(sector_id=platea.id, precio_centavos=1200000),
                    PrecioSectorCreate(sector_id=vip.id, precio_centavos=2000000),
                ],
            ))
        else:
            print("El evento demo ya existe: se conserva sin modificar sus entradas.")

        print(f"Rock Fest: evento_id={evento.id}; Platea sector_id={platea.id}; VIP sector_id={vip.id}")
        print("POST /cotizaciones/cotizar: evento_id, sector_id, cantidad=2 (Platea)")


if __name__ == "__main__":
    main()
