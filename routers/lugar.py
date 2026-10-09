from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.lugar import Lugar
from schemas.lugar import LugarCreate, LugarResponse

router = APIRouter(prefix="/lugares", tags=["Lugares"])


@router.post("/", response_model=LugarResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear un lugar")
def crear_lugar(lugar: LugarCreate, db: Session = Depends(get_db)):
    nuevo = Lugar(nombre=lugar.nombre, direccion=lugar.direccion)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/", response_model=list[LugarResponse], summary="Listar lugares")
def listar_lugares(db: Session = Depends(get_db)):
    return db.query(Lugar).all()


@router.get("/{lugar_id}", response_model=LugarResponse, summary="Buscar lugar por ID")
def obtener_lugar(lugar_id: int, db: Session = Depends(get_db)):
    lugar = db.get(Lugar, lugar_id)
    if lugar is None:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return lugar
