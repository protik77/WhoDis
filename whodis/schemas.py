"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== Auth Schemas ====================

class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ==================== API Key Schemas ====================

class APIKeyCreate(BaseModel):
    name: Optional[str] = None


class APIKeyResponse(BaseModel):
    id: int
    name: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    id: int
    name: Optional[str]
    key: str  # Only shown once on creation
    created_at: datetime


# ==================== Person Schemas ====================

class PersonBase(BaseModel):
    name: str
    notes: Optional[str] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None


class PersonResponse(PersonBase):
    id: int
    created_at: datetime
    reference_image_count: int = 0

    class Config:
        from_attributes = True


class ReferenceImageResponse(BaseModel):
    id: int
    person_id: int
    image_path: str
    engine_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Detection Schemas ====================

class DetectionRequest(BaseModel):
    engine: Optional[str] = None


class DetectionResponse(BaseModel):
    person: Optional[str] = None
    person_id: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)
    queued_for_annotation: bool = False
    engine_used: str


class DetectionLogResponse(BaseModel):
    id: int
    image_path: str
    detected_person_id: Optional[int]
    detected_person_name: Optional[str]
    confidence: Optional[float]
    engine_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Annotation Queue Schemas ====================

class AnnotationQueueItemResponse(BaseModel):
    id: int
    image_path: str
    suggested_person_id: Optional[int]
    suggested_person_name: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnnotationSubmit(BaseModel):
    person_id: Optional[int] = None  # Null = new person
    new_person_name: Optional[str] = None  # If creating new person
    ignore: bool = False  # Mark as ignore instead of annotating


# ==================== Stats Schemas ====================

class DashboardStats(BaseModel):
    total_people: int
    total_reference_images: int
    pending_annotations: int
    total_detections_24h: int
    api_keys_count: int
