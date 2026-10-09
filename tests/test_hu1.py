import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Entrada
from repositories.cotizacion import CotizacionRepository
from schemas.cotizacion import CotizacionRequest
from services.cotizacion import CotizacionService
from services.errors import CantidadInvalidaError


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def preparar_datos(client):
    lugar = client.post("/lugares/", json={"nombre": "Estadio", "direccion": "Buenos Aires"})
    assert lugar.status_code == 201
    lugar_id = lugar.json()["id"]

    platea = client.post("/sectores/", json={
        "nombre": "Platea", "capacidad_maxima": 2, "lugar_id": lugar_id
    })
    vip = client.post("/sectores/", json={
        "nombre": "VIP", "capacidad_maxima": 1, "lugar_id": lugar_id
    })
    assert platea.status_code == 201 and vip.status_code == 201
    platea_id, vip_id = platea.json()["id"], vip.json()["id"]

    evento = client.post("/eventos/", json={
        "nombre": "Rock Fest", "fecha": "2026-12-15T21:00:00", "lugar_id": lugar_id,
        "precios": [
            {"sector_id": platea_id, "precio_centavos": 1200000},
            {"sector_id": vip_id, "precio_centavos": 2000000},
        ],
    })
    assert evento.status_code == 201, evento.text
    return evento.json()["id"], platea_id, vip_id


def test_cotizacion_exitosa_y_no_reserva(client):
    api, session_factory = client
    evento_id, platea_id, _ = preparar_datos(api)
    respuesta = api.post("/cotizaciones/cotizar", json={
        "evento_id": evento_id, "sector_id": platea_id, "cantidad": 2
    })
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["precio_unitario"] == "12000.00"
    assert respuesta.json()["subtotal"] == "24000.00"
    assert respuesta.json()["total"] == "24000.00"
    with session_factory() as db:
        entradas = db.scalars(select(Entrada).where(
            Entrada.evento_id == evento_id, Entrada.sector_id == platea_id
        )).all()
        assert len(entradas) == 2
        assert all(e.estado == "Disponible" for e in entradas)


def test_capacidad_insuficiente(client):
    api, _ = client
    evento_id, _, vip_id = preparar_datos(api)
    respuesta = api.post("/cotizaciones/cotizar", json={
        "evento_id": evento_id, "sector_id": vip_id, "cantidad": 3
    })
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Capacidad insuficiente"


@pytest.mark.parametrize("cantidad", [0, -1, -3])
def test_cantidad_invalida(client, cantidad):
    api, _ = client
    respuesta = api.post("/cotizaciones/cotizar", json={
        "evento_id": 999, "sector_id": 999, "cantidad": cantidad
    })
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Cantidad inválida"


def test_disponibilidad_real_y_no_capacidad_nominal(client):
    api, session_factory = client
    evento_id, platea_id, _ = preparar_datos(api)
    with session_factory() as db:
        entrada = db.scalar(select(Entrada).where(
            Entrada.evento_id == evento_id, Entrada.sector_id == platea_id
        ))
        entrada.estado = "Emitida"
        db.commit()
    respuesta = api.post("/cotizaciones/cotizar", json={
        "evento_id": evento_id, "sector_id": platea_id, "cantidad": 2
    })
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Capacidad insuficiente"


def test_precio_no_configurado(client):
    api, _ = client
    respuesta = api.post("/cotizaciones/cotizar", json={
        "evento_id": 12345, "sector_id": 67890, "cantidad": 1
    })
    assert respuesta.status_code == 404


def test_servicio_valida_antes_de_acceder_al_repositorio():
    class RepositorioEspia:
        def obtener_precio_centavos(self, evento_id, sector_id):
            raise AssertionError("No debía consultar el repositorio")

        def contar_disponibles(self, evento_id, sector_id):
            raise AssertionError("No debía consultar el repositorio")

    servicio = CotizacionService(RepositorioEspia())
    with pytest.raises(CantidadInvalidaError, match="Cantidad inválida"):
        servicio.cotizar(CotizacionRequest(evento_id=1, sector_id=1, cantidad=0))
