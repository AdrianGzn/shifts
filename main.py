from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib

import models
import schemas
import database
import auth

from routes import user, organization, visitor, shift

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

# Registrar Routers
app.include_router(user.router)
app.include_router(organization.router)
app.include_router(visitor.router)
app.include_router(shift.router)
