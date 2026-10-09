from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from dependencies import get_pasarela_pago
from main import app
from models import Cliente, DetalleVenta, Entrada, Venta


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as api:
        yield api, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def preparar(api, capacidad=2):
    lugar = api.post("/lugares/", json={"nombre": "Estadio", "direccion": "Buenos Aires"})
    assert lugar.status_code == 201
    lugar_id = lugar.json()["id"]
    sector = api.post("/sectores/", json={
        "nombre": "Platea", "capacidad_maxima": capacidad, "lugar_id": lugar_id
    })
    assert sector.status_code == 201
    sector_id = sector.json()["id"]
    evento = api.post("/eventos/", json={
        "nombre": "Rock Fest", "fecha": "2026-12-15T21:00:00", "lugar_id": lugar_id,
        "precios": [{"sector_id": sector_id, "precio_centavos": 1200000}],
    })
    assert evento.status_code == 201, evento.text
    cliente = api.post("/clientes/", json={
        "nombre": "Ana", "email": "ana@example.com"
    })
    assert cliente.status_code == 201, cliente.text
    return cliente.json()["id"], evento.json()["id"], sector_id


def pedido(cliente_id, evento_id, sector_id, tarjeta="APROBADA", cantidad=2):
    return {
        "cliente_id": cliente_id,
        "evento_id": evento_id,
        "sector_id": sector_id,
        "cantidad": cantidad,
        "total_cotizado": str(12000 * cantidad) + ".00",
        "tarjeta_prueba": tarjeta,
    }


def test_aprobado_crea_venta_y_emite_entradas(client):
    api, sf = client
    cliente_id, evento_id, sector_id = preparar(api)
    cotizacion = api.post("/cotizaciones/cotizar", json={
        "evento_id": evento_id, "sector_id": sector_id, "cantidad": 2
    })
    assert cotizacion.status_code == 200
    assert cotizacion.json()["total"] == "24000.00"

    respuesta = api.post("/pagos/iniciar-pago", json=pedido(cliente_id, evento_id, sector_id))
    assert respuesta.status_code == 200, respuesta.text
    body = respuesta.json()
    assert body["estado"] == "Pagada"
    assert body["total"] == "24000.00"
    assert len(body["entradas"]) == 2
    assert len({e["codigo_qr"] for e in body["entradas"]}) == 2
    assert all(e["estado"] == "Emitida" for e in body["entradas"])

    with sf() as db:
        ventas = db.scalars(select(Venta)).all()
        detalles = db.scalars(select(DetalleVenta)).all()
        entradas = db.scalars(select(Entrada)).all()
        assert len(ventas) == 1 and ventas[0].estado == "Pagada"
        assert ventas[0].cliente_id == cliente_id
        assert len(detalles) == 2
        assert all(d.venta_id == ventas[0].id for d in detalles)
        assert sum(d.precio_centavos for d in detalles) == 2400000
        assert all(e.estado == "Emitida" for e in entradas)
        assert all(e.hora_ingreso is None for e in entradas)

    nueva = api.post("/cotizaciones/cotizar", json={
        "evento_id": evento_id, "sector_id": sector_id, "cantidad": 2
    })
    assert nueva.status_code == 400


def test_rechazado_no_guarda_venta_ni_emite(client):
    api, sf = client
    ids = preparar(api)
    respuesta = api.post("/pagos/iniciar-pago", json=pedido(*ids, tarjeta="RECHAZADA"))
    assert respuesta.status_code == 402, respuesta.text
    assert respuesta.json()["detail"] == "Pago denegado"
    with sf() as db:
        assert db.scalar(select(func.count(Venta.id))) == 0
        assert db.scalar(select(func.count(DetalleVenta.id))) == 0
        assert all(e.estado == "Disponible" for e in db.scalars(select(Entrada)).all())


def test_sin_stock_no_llama_pasarela(client):
    api, sf = client
    ids = preparar(api)
    with sf() as db:
        for e in db.scalars(select(Entrada)).all():
            e.estado = "Emitida"
        db.commit()

    class PasarelaEspia:
        def __init__(self):
            self.llamadas = 0

        def procesar(self, tarjeta_prueba, importe_centavos):
            self.llamadas += 1
            return True

    espia = PasarelaEspia()
    app.dependency_overrides[get_pasarela_pago] = lambda: espia
    try:
        respuesta = api.post("/pagos/iniciar-pago", json=pedido(*ids))
    finally:
        app.dependency_overrides.pop(get_pasarela_pago, None)
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["detail"] == "Los lugares seleccionados ya no se encuentran disponibles"
    assert espia.llamadas == 0
    with sf() as db:
        assert db.scalar(select(func.count(Venta.id))) == 0


def test_entrada_ids_especificos_se_respetan(client):
    api, sf = client
    ids = preparar(api, capacidad=3)
    with sf() as db:
        entradas = db.scalars(select(Entrada).order_by(Entrada.id)).all()
        seleccion = [entradas[0].id, entradas[1].id]
        entradas[0].estado = "Emitida"
        db.commit()
    datos = pedido(*ids)
    datos["entrada_ids"] = seleccion
    respuesta = api.post("/pagos/iniciar-pago", json=datos)
    assert respuesta.status_code == 409
    with sf() as db:
        assert db.scalar(select(func.count(Venta.id))) == 0


def test_monto_incorrecto_no_llama_pasarela(client):
    api, sf = client
    ids = preparar(api)
    class Espia:
        llamadas = 0
        def procesar(self, tarjeta_prueba, importe_centavos):
            self.llamadas += 1
            return True
    espia = Espia()
    app.dependency_overrides[get_pasarela_pago] = lambda: espia
    try:
        datos = pedido(*ids)
        datos["total_cotizado"] = "1.00"
        respuesta = api.post("/pagos/iniciar-pago", json=datos)
    finally:
        app.dependency_overrides.pop(get_pasarela_pago, None)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Cotización desactualizada"
    assert espia.llamadas == 0


def test_cliente_inexistente(client):
    api, _ = client
    ids = preparar(api)
    datos = pedido(*ids)
    datos["cliente_id"] = 999
    respuesta = api.post("/pagos/iniciar-pago", json=datos)
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Cliente no encontrado"


def test_cantidad_cero(client):
    api, _ = client
    ids = preparar(api)
    datos = pedido(*ids, cantidad=0)
    respuesta = api.post("/pagos/iniciar-pago", json=datos)
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Cantidad inválida"


def test_dos_pagos_concurrentes_no_venden_dos_veces(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrente.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=engine)
    sf = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with sf() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as api:
            ids = preparar(api)
            data = pedido(*ids)
            barrera = Barrier(2)
            class Espia:
                def __init__(self):
                    self.llamadas = 0
                    self.lock = Lock()
                def procesar(self, tarjeta_prueba, importe_centavos):
                    with self.lock:
                        self.llamadas += 1
                    return True
            espia = Espia()
            app.dependency_overrides[get_pasarela_pago] = lambda: espia
            def enviar():
                barrera.wait(timeout=5)
                return api.post("/pagos/iniciar-pago", json=data)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futuros = [pool.submit(enviar) for _ in range(2)]
                respuestas = [f.result(timeout=20) for f in futuros]
            assert sorted(r.status_code for r in respuestas) == [200, 409], [r.text for r in respuestas]
            assert espia.llamadas == 1
            with sf() as db:
                assert db.scalar(select(func.count(Venta.id))) == 1
                assert db.scalar(select(func.count(DetalleVenta.id))) == 2
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
