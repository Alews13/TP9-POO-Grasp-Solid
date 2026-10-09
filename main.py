from fastapi import FastAPI
from database import Base, engine
import models  # Importa TODOS los modelos antes de crear las tablas.
from routers import acceso, cliente, cotizacion, evento, lugar, pago, sector

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartTicket API",
    description="API REST de venta de entradas. HU1 cotización, HU2 pago/emisión y HU3 control de acceso con GRASP y SOLID.",
    version="1.3.0",
)

app.include_router(lugar.router)
app.include_router(cliente.router)
app.include_router(sector.router)
app.include_router(evento.router)
app.include_router(cotizacion.router)
app.include_router(pago.router)
app.include_router(acceso.router)


@app.get("/", tags=["General"], summary="Comprobar funcionamiento")
def root():
    return {"message": "SmartTicket API funcionando"}
