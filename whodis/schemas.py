"""Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ==================== Auth Schemas ====================


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ==================== API Key Schemas ====================


class APIKeyCreate(BaseModel):
    name: str | None = None


class APIKeyResponse(BaseModel):
    id: int
    name: str | None
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str | None
    key: str  # Only shown once on creation
    created_at: datetime


# ==================== Person Schemas ====================


class PersonBase(BaseModel):
    name: str
    notes: str | None = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None


class PersonResponse(PersonBase):
    id: int
    created_at: datetime
    reference_image_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ReferenceImageResponse(BaseModel):
    id: int
    person_id: int
    image_path: str
    engine_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Detection Schemas ====================


class DetectionRequest(BaseModel):
    engine: str | None = None


class DetectionResponse(BaseModel):
    person: str | None = None
    person_id: int | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    queued_for_annotation: bool = False
    engine_used: str


class DetectionLogResponse(BaseModel):
    id: int
    image_path: str
    detected_person_id: int | None
    detected_person_name: str | None
    confidence: float | None
    engine_used: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Annotation Queue Schemas ====================


class AnnotationQueueItemResponse(BaseModel):
    id: int
    image_path: str
    suggested_person_id: int | None
    suggested_person_name: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnotationSubmit(BaseModel):
    person_id: int | None = None  # Null = new person
    new_person_name: str | None = None  # If creating new person
    ignore: bool = False  # Mark as ignore instead of annotating


# ==================== Stats Schemas ====================


class DashboardStats(BaseModel):
    total_people: int
    total_reference_images: int
    pending_annotations: int
    total_detections_24h: int
    api_keys_count: int
