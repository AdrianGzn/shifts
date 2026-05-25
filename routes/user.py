import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import hashlib

import models
import schemas
import auth
from database import SessionLocal

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.User).offset(skip).limit(limit).all()

@router.get("/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user

@router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(**user.model_dump(exclude={"password"}))
    db_user.password = hashlib.sha256(user.password.encode()).hexdigest()
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/me", response_model=schemas.User)
def update_profile(user: schemas.UserUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token no contiene email")
    
    db_user = db.query(models.User).filter(models.User.mail == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    update_data = user.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = hashlib.sha256(update_data["password"].encode()).hexdigest()
        
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    update_data = user.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = hashlib.sha256(update_data["password"].encode()).hexdigest()
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(db_user)
    db.commit()
    return {"detail": "Usuario eliminado correctamente"}
