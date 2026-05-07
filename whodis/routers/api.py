"""API routes for client integration."""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Security,
    UploadFile,
    status,
)
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from whodis.auth import hash_api_key
from whodis.models import get_db
from whodis.schemas import DetectionResponse
from whodis.services.detection import detect_person

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    image: UploadFile = File(...),
    engine: str | None = Form(None),
    db: Session = Depends(get_db),
    credentials=Security(security),
):
    """
    Detect a person in an image.

    - **image**: Image file to analyze
    - **engine**: Optional engine to use (defaults to configured default)

    Returns person name if recognized, or queues for annotation if unknown.
    Requires API key authentication via Authorization header.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify API key
    key = credentials.credentials
    key_hash = hash_api_key(key)

    from whodis.models import APIKey

    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used
    from datetime import datetime

    api_key.last_used_at = datetime.utcnow()
    db.commit()

    # Read image data
    image_data = await image.read()

    # Perform detection
    result = await detect_person(
        image_data=image_data,
        db=db,
        engine_name=engine,
        api_key_id=api_key.id,
    )

    return result


@router.get("/engines")
async def list_engines(
    db: Session = Depends(get_db),
    credentials=Security(security),
):
    """List available detection engines."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    # Verify API key
    key = credentials.credentials
    key_hash = hash_api_key(key)

    from whodis.models import APIKey

    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    from whodis.config import DEFAULT_ENGINE
    from whodis.engines.registry import EngineRegistry

    return {
        "engines": EngineRegistry.list_engines(),
        "default": DEFAULT_ENGINE,
    }
