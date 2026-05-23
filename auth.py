import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv

load_dotenv()

# Client IDs de Google para Web y Móvil
GOOGLE_WEB_CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID")
GOOGLE_MOBILE_CLIENT_ID = os.getenv("GOOGLE_MOBILE_CLIENT_ID")

# Lista de audiences válidos: acepta tokens generados tanto por web como por móvil
VALID_CLIENT_IDS = [cid for cid in [GOOGLE_WEB_CLIENT_ID, GOOGLE_MOBILE_CLIENT_ID] if cid]

security = HTTPBearer()

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica el ID token de Google.
    Acepta tokens emitidos para el cliente Web o el cliente Móvil (Android/iOS).
    """
    token = credentials.credentials

    # Intentar verificar con cada client ID registrado
    for client_id in VALID_CLIENT_IDS:
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
            return idinfo
        except ValueError:
            continue

    # Si ningún client ID validó el token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticacion de Google invalido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
