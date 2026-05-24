import os
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv

load_dotenv()

# Client IDs de Google para Web y Móvil
# Fallback hardcoded en caso de que .env no se cargue en el servidor remoto
GOOGLE_WEB_CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID", "777549895961-o3vshogh18s3b2jesccn46n4btm01r72.apps.googleusercontent.com")
GOOGLE_MOBILE_CLIENT_ID = os.getenv("GOOGLE_MOBILE_CLIENT_ID", "777549895961-l48kgjfp6ht3bjg47lavb1o618hbhtgd.apps.googleusercontent.com")

# JWT Custom Secret
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-1234")
JWT_ALGORITHM = "HS256"

# Lista de audiences válidos: acepta tokens generados tanto por web como por móvil
VALID_CLIENT_IDS = [cid for cid in [GOOGLE_WEB_CLIENT_ID, GOOGLE_MOBILE_CLIENT_ID] if cid]

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica si el token es un ID token de Google o un JWT propio.
    """
    token = credentials.credentials

    # 1. Intentar verificar como JWT propio (standard login)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        pass # No es un JWT válido propio, intentar con Google

    # 2. Intentar verificar con cada client ID registrado de Google
    for client_id in VALID_CLIENT_IDS:
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
            return idinfo
        except ValueError:
            continue

    # Si ningún método funcionó
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
