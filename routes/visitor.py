import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
import auth
from database import SessionLocal

router = APIRouter(prefix="/visitors", tags=["Visitors"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[schemas.Visitor])
def read_visitors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Visitor).offset(skip).limit(limit).all()

@router.get("/{visitor_id}", response_model=schemas.Visitor)
def read_visitor(visitor_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not db_visitor:
        raise HTTPException(status_code=404, detail="Visitante no encontrado")
    return db_visitor

@router.post("/", response_model=schemas.Visitor)
def create_visitor(visitor: schemas.VisitorCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = models.Visitor(**visitor.model_dump())
    db.add(db_visitor)
    db.commit()
    db.refresh(db_visitor)
    return db_visitor

@router.put("/{visitor_id}", response_model=schemas.Visitor)
def update_visitor(visitor_id: int, visitor: schemas.VisitorUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not db_visitor:
        raise HTTPException(status_code=404, detail="Visitante no encontrado")
    update_data = visitor.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_visitor, key, value)
    db.commit()
    db.refresh(db_visitor)
    return db_visitor

@router.delete("/{visitor_id}")
def delete_visitor(visitor_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not db_visitor:
        raise HTTPException(status_code=404, detail="Visitante no encontrado")
    db.delete(db_visitor)
    db.commit()
    return {"detail": "Visitante eliminado correctamente"}
