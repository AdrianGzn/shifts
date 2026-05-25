from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, time, datetime
from enum import Enum

class OrganizationType(str, Enum):
    empresa = "empresa"
    oficina = "oficina"
    planta = "planta"
    comercial = "comercial"
    otro = "otro"

class Role(str, Enum):
    empleado = "empleado"
    supervisor = "supervisor"
    guardia = "guardia"
    admin = "admin"

class EventType(str, Enum):
    entry = "entry"
    exit = "exit"

# --- Organization ---
class OrganizationBase(BaseModel):
    type: OrganizationType = OrganizationType.empresa
    name: str
    address: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    type: Optional[OrganizationType] = None
    name: Optional[str] = None
    address: Optional[str] = None

class Organization(OrganizationBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- User ---
class UserBase(BaseModel):
    idOrganization: Optional[int] = None
    name: str
    mail: Optional[str] = None
    role: Role = Role.empleado
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    idOrganization: Optional[int] = None
    name: Optional[str] = None
    mail: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class User(UserBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Shift ---
class ShiftBase(BaseModel):
    idUser: Optional[int] = None
    idVisitor: Optional[int] = None
    date: date
    startTime: time
    endTime: Optional[time] = None
    notes: Optional[str] = None

class ShiftCreate(ShiftBase):
    pass

class ShiftUpdate(BaseModel):
    idUser: Optional[int] = None
    idVisitor: Optional[int] = None
    date: Optional[date] = None
    startTime: Optional[time] = None
    endTime: Optional[time] = None
    notes: Optional[str] = None

class Shift(ShiftBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Visitor ---
class VisitorBase(BaseModel):
    fullName: str
    document_id: Optional[str] = None
    company: Optional[str] = None
    reason: str
    phone: Optional[str] = None

class VisitorCreate(VisitorBase):
    pass

class VisitorUpdate(BaseModel):
    fullName: Optional[str] = None
    document_id: Optional[str] = None
    company: Optional[str] = None
    reason: Optional[str] = None
    phone: Optional[str] = None

class Visitor(VisitorBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Access Log ---
class AccessLogBase(BaseModel):
    idUser: Optional[int] = None
    idVisitor: Optional[int] = None
    idGuard: int
    event_type: EventType
    notes: Optional[str] = None

class AccessLogCreate(AccessLogBase):
    pass

class AccessLogUpdate(BaseModel):
    idUser: Optional[int] = None
    idVisitor: Optional[int] = None
    idGuard: Optional[int] = None
    event_type: Optional[EventType] = None
    notes: Optional[str] = None

class AccessLog(AccessLogBase):
    id: int
    timestamp_event: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
