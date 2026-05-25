import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from pydantic import BaseModel

import models
import schemas
import auth
from database import SessionLocal

router = APIRouter(prefix="/shifts", tags=["Shifts"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ScanPayload(BaseModel):
    person_id: int
    is_visitor: bool = False

@router.post("/scan", response_model=schemas.Shift)
def scan_shift(payload: ScanPayload, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    # 1. Verificar si existe la persona
    if payload.is_visitor:
        person = db.query(models.Visitor).filter(models.Visitor.id == payload.person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Visitante no encontrado")
        filter_condition = (models.Shift.idVisitor == payload.person_id)
    else:
        person = db.query(models.User).filter(models.User.id == payload.person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Usuario/Empleado no encontrado")
        filter_condition = (models.Shift.idUser == payload.person_id)

    today = date.today()
    now_time = datetime.now().time()

    # Buscar si tiene una entrada pendiente (endTime es nulo)
    pending_shift = db.query(models.Shift).filter(
        filter_condition,
        models.Shift.date == today,
        models.Shift.endTime == None
    ).first()

    if pending_shift:
        # Registrar Salida (PUT lógico)
        pending_shift.endTime = now_time
        db.commit()
        db.refresh(pending_shift)
        return pending_shift
    else:
        # Registrar Entrada (POST lógico)
        new_shift = models.Shift(
            idUser=payload.person_id if not payload.is_visitor else None,
            idVisitor=payload.person_id if payload.is_visitor else None,
            date=today,
            startTime=now_time,
            endTime=None
        )
        db.add(new_shift)
        db.commit()
        db.refresh(new_shift)
        return new_shift

@router.get("/", response_model=List[schemas.Shift])
def read_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Shift).offset(skip).limit(limit).all()

@router.get("/{shift_id}", response_model=schemas.Shift)
def read_shift(shift_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return db_shift

@router.post("/", response_model=schemas.Shift)
def create_shift(shift: schemas.ShiftCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = models.Shift(**shift.model_dump())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift

@router.put("/{shift_id}", response_model=schemas.Shift)
def update_shift(shift_id: int, shift: schemas.ShiftUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    update_data = shift.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_shift, key, value)
    db.commit()
    db.refresh(db_shift)
    return db_shift

@router.delete("/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    db.delete(db_shift)
    db.commit()
    return {"detail": "Turno eliminado correctamente"}
