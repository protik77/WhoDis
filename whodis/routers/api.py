"""API routes for client integration."""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
)
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from whodis.auth import require_api_key
from whodis.models import User, get_db
from whodis.schemas import DetectionResponse
from whodis.services.detection import detect_person

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/detect", response_model=DetectionResponse | list[DetectionResponse])
async def detect(
    image: UploadFile = File(...),
    engine: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_api_key),
) -> DetectionResponse | list[DetectionResponse]:
    """
    Detect a person in an image.

    - **image**: Image file to analyze
    - **engine**: Optional engine to use (defaults to configured default)

    Returns person name if recognized, or queues for annotation if unknown.
    Requires API key authentication via Authorization header.
    """
    # Read image data
    image_data = await image.read()

    # Perform detection
    result = await detect_person(
        image_data=image_data,
        db=db,
        engine_name=engine,
        api_key_id=None,  # We don't have the API key ID easily here without more work, but we have the user
    )

    return result


@router.get("/engines")
async def list_engines(
    db: Session = Depends(get_db),
    user: User = Depends(require_api_key),
) -> dict:
    """List available detection engines."""
    from whodis.config import DEFAULT_ENGINE
    from whodis.engines.registry import EngineRegistry

    return {
        "engines": EngineRegistry.list_engines(),
        "default": DEFAULT_ENGINE,
    }
