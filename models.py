from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, Date, Time, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class OrganizationType(enum.Enum):
    empresa = "empresa"
    oficina = "oficina"
    planta = "planta"
    comercial = "comercial"
    otro = "otro"

class Role(enum.Enum):
    empleado = "empleado"
    supervisor = "supervisor"
    guardia = "guardia"
    admin = "admin"

class EventType(enum.Enum):
    entry = "entry"
    exit = "exit"

class Organization(Base):
    __tablename__ = "organization"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(OrganizationType), default=OrganizationType.empresa, nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    users = relationship("User", back_populates="organization")

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    idOrganization = Column(Integer, ForeignKey("organization.id"), nullable=True)
    name = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)
    mail = Column(String(100), unique=True, index=True, nullable=True)
    role = Column(SQLEnum(Role), default=Role.empleado, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    organization = relationship("Organization", back_populates="users")
    shifts = relationship("Shift", back_populates="user")

class Shift(Base):
    __tablename__ = "shift"
    id = Column(Integer, primary_key=True, index=True)
    idUser = Column(Integer, ForeignKey("user.id"), nullable=False)
    date = Column(Date, nullable=False)
    startTime = Column(Time, nullable=False)
    endTime = Column(Time, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    user = relationship("User", back_populates="shifts")

class Visitor(Base):
    __tablename__ = "visitor"
    id = Column(Integer, primary_key=True, index=True)
    fullName = Column(String(100), nullable=False)
    document_id = Column(String(50), nullable=True)
    company = Column(String(100), nullable=True)
    reason = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

class AccessLog(Base):
    __tablename__ = "access_log"
    id = Column(Integer, primary_key=True, index=True)
    idUser = Column(Integer, ForeignKey("user.id"), nullable=True)
    idVisitor = Column(Integer, ForeignKey("visitor.id"), nullable=True)
    idGuard = Column(Integer, ForeignKey("user.id"), nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    timestamp_event = Column(TIMESTAMP, server_default=func.now())
    notes = Column(String(255), nullable=True)

    user = relationship("User", foreign_keys=[idUser])
    visitor = relationship("Visitor", foreign_keys=[idVisitor])
    guard = relationship("User", foreign_keys=[idGuard])
