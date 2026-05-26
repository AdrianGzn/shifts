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

from pydantic import BaseModel
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login", tags=["Auth"])
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.mail == login_req.email) | (models.User.name == login_req.email)
    ).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario/Correo o contraseña incorrectos")
    
    hashed_pass = hashlib.sha256(login_req.password.encode()).hexdigest()
    if db_user.password != hashed_pass:
        raise HTTPException(status_code=401, detail="Usuario/Correo o contraseña incorrectos")
        
    access_token = auth.create_access_token(
        data={"sub": str(db_user.id), "email": db_user.mail, "name": db_user.name}
    )
    return {"access_token": access_token, "token_type": "bearer", "user": db_user}

class GoogleLoginRequest(BaseModel):
    token: str = None
    idToken: str = None

@app.post("/auth/google", tags=["Auth"])
def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    # 1. Obtener token de idToken o token para soporte multiplataforma
    google_token = req.idToken or req.token
    if not google_token:
        raise HTTPException(
            status_code=400,
            detail="Falta el token de Google. Debe proporcionar 'idToken' o 'token'."
        )

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests
        
        idinfo = None
        last_error = None
        
        # Verificar contra todos los Client IDs válidos (Web y Móvil)
        for client_id in auth.VALID_CLIENT_IDS:
            try:
                idinfo = id_token.verify_oauth2_token(google_token, requests.Request(), client_id)
                break
            except ValueError as ve:
                last_error = f"ValueError para client_id {client_id}: {str(ve)}"
                continue
            except Exception as e:
                last_error = f"Error para client_id {client_id}: {str(e)}"
                continue
                
        if not idinfo:
            detail_msg = "Token de Google inválido o no coincide con los Client IDs registrados."
            if last_error:
                detail_msg += f" Detalle del último intento: {last_error}"
            raise HTTPException(status_code=401, detail=detail_msg)
            
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=400,
            detail=f"Error durante el proceso de verificación de Google: {str(e)}. Stacktrace: {traceback.format_exc()}"
        )

    email = idinfo.get("email")
    name = idinfo.get("name", "Usuario")

    try:
        db_user = db.query(models.User).filter(models.User.mail == email).first()
        if not db_user:
            return {"needs_registration": True, "email": email, "name": name}
        
        access_token = auth.create_access_token(
            data={"sub": str(db_user.id), "email": db_user.mail, "name": db_user.name}
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "idOrganization": db_user.idOrganization,
                "name": db_user.name,
                "mail": db_user.mail,
                "role": db_user.role.value if hasattr(db_user.role, 'value') else str(db_user.role),
                "is_active": db_user.is_active
            },
            "needs_registration": False
        }
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error en la base de datos o en la serialización del usuario: {str(e)}. Stacktrace: {traceback.format_exc()}"
        )

# ============================================================
# ORGANIZACIONES - CRUD completo
# ============================================================

@app.get("/organizations/", response_model=List[schemas.Organization], tags=["Organizations"])
def read_organizations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Organization).offset(skip).limit(limit).all()

@app.get("/organizations/{org_id}", response_model=schemas.Organization, tags=["Organizations"])
def read_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organizacion no encontrada")
    return db_org

@app.post("/organizations/", response_model=schemas.Organization, tags=["Organizations"])
def create_organization(org: schemas.OrganizationCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = models.Organization(**org.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

@app.put("/organizations/{org_id}", response_model=schemas.Organization, tags=["Organizations"])
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

@app.delete("/organizations/{org_id}", tags=["Organizations"])
def delete_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organizacion no encontrada")
    db.delete(db_org)
    db.commit()
    return {"detail": "Organizacion eliminada correctamente"}

# ============================================================
# USERS - CRUD completo
# ============================================================

@app.get("/users/", response_model=List[schemas.User], tags=["Users"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.User).offset(skip).limit(limit).all()

@app.get("/users/{user_id}", response_model=schemas.User, tags=["Users"])
def read_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user

@app.post("/users/", response_model=schemas.User, tags=["Users"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(**user.model_dump(exclude={"password"}))
    # Encriptar clave igual que en script (SHA256)
    db_user.password = hashlib.sha256(user.password.encode()).hexdigest()
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/users/{user_id}", response_model=schemas.User, tags=["Users"])
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    update_data = user.model_dump(exclude_unset=True)
    # Si se actualiza la contraseña, encriptarla
    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = hashlib.sha256(update_data["password"].encode()).hexdigest()
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(db_user)
    db.commit()
    return {"detail": "Usuario eliminado correctamente"}

# ============================================================
# SHIFTS - CRUD completo
# ============================================================

@app.get("/shifts/", response_model=List[schemas.Shift], tags=["Shifts"])
def read_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Shift).offset(skip).limit(limit).all()

@app.get("/shifts/{shift_id}", response_model=schemas.Shift, tags=["Shifts"])
def read_shift(shift_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return db_shift

@app.post("/shifts/", response_model=schemas.Shift, tags=["Shifts"])
def create_shift(shift: schemas.ShiftCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = models.Shift(**shift.model_dump())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift

@app.put("/shifts/{shift_id}", response_model=schemas.Shift, tags=["Shifts"])
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

@app.delete("/shifts/{shift_id}", tags=["Shifts"])
def delete_shift(shift_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    db.delete(db_shift)
    db.commit()
    return {"detail": "Turno eliminado correctamente"}

# ============================================================
# VISITORS - CRUD completo
# ============================================================

@app.get("/visitors/", response_model=List[schemas.Visitor], tags=["Visitors"])
def read_visitors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.Visitor).offset(skip).limit(limit).all()

@app.get("/visitors/{visitor_id}", response_model=schemas.Visitor, tags=["Visitors"])
def read_visitor(visitor_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not db_visitor:
        raise HTTPException(status_code=404, detail="Visitante no encontrado")
    return db_visitor

@app.post("/visitors/", response_model=schemas.Visitor, tags=["Visitors"])
def create_visitor(visitor: schemas.VisitorCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = models.Visitor(**visitor.model_dump())
    db.add(db_visitor)
    db.commit()
    db.refresh(db_visitor)
    return db_visitor

@app.put("/visitors/{visitor_id}", response_model=schemas.Visitor, tags=["Visitors"])
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

@app.delete("/visitors/{visitor_id}", tags=["Visitors"])
def delete_visitor(visitor_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not db_visitor:
        raise HTTPException(status_code=404, detail="Visitante no encontrado")
    db.delete(db_visitor)
    db.commit()
    return {"detail": "Visitante eliminado correctamente"}

# ============================================================
# ACCESS LOGS - CRUD completo
# ============================================================

@app.get("/access-logs/", response_model=List[schemas.AccessLog], tags=["Access Logs"])
def read_access_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    return db.query(models.AccessLog).offset(skip).limit(limit).all()

@app.get("/access-logs/{log_id}", response_model=schemas.AccessLog, tags=["Access Logs"])
def read_access_log(log_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_log = db.query(models.AccessLog).filter(models.AccessLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Registro de acceso no encontrado")
    return db_log

@app.post("/access-logs/", response_model=schemas.AccessLog, tags=["Access Logs"])
def create_access_log(log: schemas.AccessLogCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    if (log.idUser is None and log.idVisitor is None) or (log.idUser is not None and log.idVisitor is not None):
        raise HTTPException(status_code=400, detail="Debe especificar idUser o idVisitor, no ambos o ninguno.")
    db_log = models.AccessLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@app.put("/access-logs/{log_id}", response_model=schemas.AccessLog, tags=["Access Logs"])
def update_access_log(log_id: int, log: schemas.AccessLogUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_log = db.query(models.AccessLog).filter(models.AccessLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Registro de acceso no encontrado")
    update_data = log.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_log, key, value)
    db.commit()
    db.refresh(db_log)
    return db_log

@app.delete("/access-logs/{log_id}", tags=["Access Logs"])
def delete_access_log(log_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    db_log = db.query(models.AccessLog).filter(models.AccessLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Registro de acceso no encontrado")
    db.delete(db_log)
    db.commit()
    return {"detail": "Registro de acceso eliminado correctamente"}

# ============================================================
# SEND MAIL - Conecta con el microservicio de correos
# ============================================================

import requests as http_requests

MAIL_MICROSERVICE_URL = "http://localhost:8082/api/mail/send"

@app.post("/sendMail", tags=["Mail"])
def send_mail(req: schemas.SendMailRequest, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user_token)):
    # 1. Buscar emisor
    emisor = db.query(models.User).filter(models.User.id == req.idEmisor).first()
    if not emisor:
        raise HTTPException(status_code=404, detail="Emisor no encontrado")

    # 2. Buscar receptor
    receptor = db.query(models.User).filter(models.User.id == req.idReceptor).first()
    if not receptor:
        raise HTTPException(status_code=404, detail="Receptor no encontrado")

    if not receptor.mail:
        raise HTTPException(status_code=400, detail="El receptor no tiene correo registrado")

    # 3. Buscar organización del emisor
    if not emisor.idOrganization:
        raise HTTPException(status_code=400, detail="El emisor no tiene organización asignada")

    organizacion = db.query(models.Organization).filter(models.Organization.id == emisor.idOrganization).first()
    if not organizacion:
        raise HTTPException(status_code=404, detail="Organización del emisor no encontrada")

    # 4. Armar payload para el microservicio
    payload = {
        "organizationName": organizacion.name,
        "organizationId": str(organizacion.id),
        "senderName": emisor.name,
        "senderId": str(emisor.id),
        "senderMessage": req.mensaje,
        "recipientName": receptor.name,
        "recipientId": str(receptor.id),
        "recipientEmail": receptor.mail
    }

    # 5. Enviar al microservicio
    try:
        response = http_requests.post(MAIL_MICROSERVICE_URL, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="No se pudo conectar con el microservicio de correos. Asegúrate de que esté corriendo en localhost:8082")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="El microservicio de correos tardó demasiado en responder")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error del microservicio: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado al enviar correo: {str(e)}")
