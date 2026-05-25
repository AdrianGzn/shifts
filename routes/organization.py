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

router = APIRouter(prefix="/organizations", tags=["Organizations"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[schemas.Organization])
def read_organizations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Organization).offset(skip).limit(limit).all()

@router.get("/{org_id}", response_model=schemas.Organization)
def read_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organizacion no encontrada")
    return db_org

@router.post("/", response_model=schemas.Organization)
def create_organization(org: schemas.OrganizationCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = models.Organization(**org.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

@router.put("/{org_id}", response_model=schemas.Organization)
def update_organization(org_id: int, org: schemas.OrganizationUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organizacion no encontrada")
    update_data = org.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)
    db.commit()
    db.refresh(db_org)
    return db_org

@router.delete("/{org_id}")
def delete_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organizacion no encontrada")
    db.delete(db_org)
    db.commit()
    return {"detail": "Organizacion eliminada correctamente"}
