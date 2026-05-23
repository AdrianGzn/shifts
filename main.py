from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database, auth
import hashlib

# Inicializar Base por si no están creadas las tablas, aunque el script SQL ya existe.
# models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Transaccional API",
    description="API con FastAPI, MySQL y Autenticación de Google para control de accesos.",
    version="1.0.0"
)

# Dependency para obtener sesion de BDD
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Root"])
def root():
    return {"message": "Bienvenido a la API de Accesos. Ve a /docs para ver la documentacion de Swagger UI."}

# --- Organizaciones ---
@app.get("/organizations/", response_model=List[schemas.Organization], tags=["Organizations"])
def read_organizations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Organization).offset(skip).limit(limit).all()

@app.post("/organizations/", response_model=schemas.Organization, tags=["Organizations"])
def create_organization(org: schemas.OrganizationCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = models.Organization(**org.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

# --- Users ---
@app.get("/users/", response_model=List[schemas.User], tags=["Users"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.User).offset(skip).limit(limit).all()

@app.post("/users/", response_model=schemas.User, tags=["Users"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = models.User(**user.model_dump(exclude={"password"}))
    # Encriptar clave igual que en script (SHA256)
    db_user.password = hashlib.sha256(user.password.encode()).hexdigest()
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Shifts ---
@app.get("/shifts/", response_model=List[schemas.Shift], tags=["Shifts"])
def read_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Shift).offset(skip).limit(limit).all()

@app.post("/shifts/", response_model=schemas.Shift, tags=["Shifts"])
def create_shift(shift: schemas.ShiftCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = models.Shift(**shift.model_dump())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift

# --- Visitors ---
@app.get("/visitors/", response_model=List[schemas.Visitor], tags=["Visitors"])
def read_visitors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Visitor).offset(skip).limit(limit).all()

@app.post("/visitors/", response_model=schemas.Visitor, tags=["Visitors"])
def create_visitor(visitor: schemas.VisitorCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = models.Visitor(**visitor.model_dump())
    db.add(db_visitor)
    db.commit()
    db.refresh(db_visitor)
    return db_visitor

# --- Access Logs ---
@app.get("/access-logs/", response_model=List[schemas.AccessLog], tags=["Access Logs"])
def read_access_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.AccessLog).offset(skip).limit(limit).all()

@app.post("/access-logs/", response_model=schemas.AccessLog, tags=["Access Logs"])
def create_access_log(log: schemas.AccessLogCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    if (log.idUser is None and log.idVisitor is None) or (log.idUser is not None and log.idVisitor is not None):
        raise HTTPException(status_code=400, detail="Debe especificar idUser o idVisitor, no ambos o ninguno.")
    db_log = models.AccessLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
