from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from dependencies import get_reloj
from main import app
from models import DetalleVenta, Entrada, Venta


INSTANTE = datetime(2026, 12, 16, 0, 30, 45, 123456, tzinfo=timezone.utc)


class RelojFijo:
    def __init__(self, instante=INSTANTE):
        self.instante = instante

    def ahora(self):
        return self.instante


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    sf = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with sf() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_reloj] = lambda: RelojFijo()
    with TestClient(app) as api:
        yield api, sf
    app.dependency_overrides.clear()
    engine.dispose()


def preparar(api, capacidad=2):
    lugar = api.post("/lugares/", json={"nombre": "Estadio", "direccion": "Buenos Aires"})
    assert lugar.status_code == 201, lugar.text
    lugar_id = lugar.json()["id"]
    sector = api.post("/sectores/", json={
        "nombre": "Platea", "capacidad_maxima": capacidad, "lugar_id": lugar_id,
    })
    assert sector.status_code == 201, sector.text
    sector_id = sector.json()["id"]
    evento = api.post("/eventos/", json={
        "nombre": "Rock Fest", "fecha": "2026-12-15T21:00:00", "lugar_id": lugar_id,
        "precios": [{"sector_id": sector_id, "precio_centavos": 1200000}],
    })
    assert evento.status_code == 201, evento.text
    cliente = api.post("/clientes/", json={"nombre": "Ana", "email": "ana@example.com"})
    assert cliente.status_code == 201, cliente.text
    return cliente.json()["id"], evento.json()["id"], sector_id


def emitir(api, ids, cantidad=1):
    cliente_id, evento_id, sector_id = ids
    respuesta = api.post("/pagos/iniciar-pago", json={
        "cliente_id": cliente_id,
        "evento_id": evento_id,
        "sector_id": sector_id,
        "cantidad": cantidad,
        "total_cotizado": f"{12000*cantidad}.00",
        "tarjeta_prueba": "APROBADA",
    })
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["entradas"]


def test_ingreso_exitoso_registra_hora_exacta_y_utiliza_entrada(client):
    api, sf = client
    ids = preparar(api)
    entrada = emitir(api, ids)[0]
    respuesta = api.post("/acceso/validar", json={"codigo_qr": entrada["codigo_qr"]})
    assert respuesta.status_code == 200, respuesta.text
    body = respuesta.json()
    assert body["mensaje"] == "Acceso Permitido"
    assert body["estado"] == "Utilizada"
    assert body["entrada_id"] == entrada["id"]
    assert body["evento_id"] == ids[1]
    assert datetime.fromisoformat(body["hora_ingreso"].replace("Z", "+00:00")) == INSTANTE
    with sf() as db:
        guardada = db.get(Entrada, entrada["id"])
        assert guardada.estado == "Utilizada"
        assert guardada.hora_ingreso == INSTANTE.replace(tzinfo=None)


def test_qr_duplicado_rechaza_y_preserva_hora_original(client):
    api, sf = client
    ids = preparar(api)
    entrada = emitir(api, ids)[0]
    qr = entrada["codigo_qr"]
    assert api.post("/acceso/validar", json={"codigo_qr": qr}).status_code == 200
    app.dependency_overrides[get_reloj] = lambda: RelojFijo(
        datetime(2026, 12, 16, 1, 40, 55, tzinfo=timezone.utc)
    )
    respuesta = api.post("/acceso/validar", json={"codigo_qr": qr})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Entrada ya utilizada"
    with sf() as db:
        guardada = db.get(Entrada, entrada["id"])
        assert guardada.hora_ingreso == INSTANTE.replace(tzinfo=None)


def test_qr_inexistente_retorna_404(client):
    api, _ = client
    respuesta = api.post("/acceso/validar", json={"codigo_qr": "codigo-adulterado"})
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Ticket Inválido o Inexistente"


@pytest.mark.parametrize("estado", ["Disponible", "Reservada"])
def test_entrada_no_emitida_rechazada(client, estado):
    api, sf = client
    ids = preparar(api)
    with sf() as db:
        entrada = db.scalar(select(Entrada))
        qr = entrada.codigo_qr
        entrada.estado = estado
        db.commit()
    respuesta = api.post("/acceso/validar", json={"codigo_qr": qr})
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Ticket no emitido / Falta de pago"
    with sf() as db:
        entrada = db.scalar(select(Entrada).where(Entrada.codigo_qr == qr))
        assert entrada.estado == estado
        assert entrada.hora_ingreso is None


def test_emitida_sin_venta_pagada_tampoco_ingresa(client):
    api, sf = client
    preparar(api)
    with sf() as db:
        entrada = db.scalar(select(Entrada))
        entrada.estado = "Emitida"
        qr = entrada.codigo_qr
        db.commit()
    respuesta = api.post("/acceso/validar", json={"codigo_qr": qr})
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Ticket no emitido / Falta de pago"


def test_evento_fuera_del_dia_rechazado(client):
    api, sf = client
    ids = preparar(api)
    entrada = emitir(api, ids)[0]
    app.dependency_overrides[get_reloj] = lambda: RelojFijo(
        datetime(2026, 12, 17, 15, 0, tzinfo=timezone.utc)
    )
    respuesta = api.post("/acceso/validar", json={"codigo_qr": entrada["codigo_qr"]})
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "El ticket no corresponde al evento del día"
    with sf() as db:
        guardada = db.get(Entrada, entrada["id"])
        assert guardada.estado == "Emitida"
        assert guardada.hora_ingreso is None


def test_entrada_emitida_pero_con_hora_existente_no_sobreescribe(client):
    api, sf = client
    ids = preparar(api)
    entrada = emitir(api, ids)[0]
    with sf() as db:
        guardada = db.get(Entrada, entrada["id"])
        guardada.hora_ingreso = INSTANTE.replace(tzinfo=None)
        db.commit()
    respuesta = api.post("/acceso/validar", json={"codigo_qr": entrada["codigo_qr"]})
    assert respuesta.status_code == 409
    with sf() as db:
        assert db.get(Entrada, entrada["id"]).hora_ingreso == INSTANTE.replace(tzinfo=None)


def test_swagger_documenta_endpoint():
    ruta = app.openapi()["paths"]["/acceso/validar"]["post"]
    assert ruta["summary"] == "Validar QR e ingresar al evento (HU3)"
    assert set(["200", "403", "404", "409"]).issubset(ruta["responses"])


def test_dos_escaneos_concurrentes_solo_permiten_un_ingreso(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'accesos.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=engine)
    sf = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with sf() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_reloj] = lambda: RelojFijo()
    try:
        with TestClient(app) as api:
            ids = preparar(api, capacidad=1)
            entrada = emitir(api, ids)[0]
            barrera = Barrier(2)

            def escanear():
                barrera.wait(timeout=5)
                return api.post("/acceso/validar", json={"codigo_qr": entrada["codigo_qr"]})

            with ThreadPoolExecutor(max_workers=2) as pool:
                futuros = [pool.submit(escanear) for _ in range(2)]
                respuestas = [f.result(timeout=20) for f in futuros]
            assert sorted(r.status_code for r in respuestas) == [200, 409], [r.text for r in respuestas]
            with sf() as db:
                guardada = db.get(Entrada, entrada["id"])
                assert guardada.estado == "Utilizada"
                assert guardada.hora_ingreso == INSTANTE.replace(tzinfo=None)
                assert len(db.scalars(select(Venta)).all()) == 1
                assert len(db.scalars(select(DetalleVenta)).all()) == 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
