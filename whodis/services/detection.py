"""Detection service for coordinating detection requests."""

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Session

from whodis.config import MAX_IMAGE_SIZE, UPLOAD_DIR
from whodis.engines.registry import EngineRegistry
from whodis.models import AnnotationQueue, DetectionLog, Person, ReferenceImage
from whodis.schemas import DetectionResponse


async def save_upload_file(file: UploadFile) -> tuple[Path, bytes]:
    """Save an uploaded file to disk."""
    # Generate unique filename
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]:
        ext = ".jpg"

    filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / filename

    # Save file
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise ValueError(
            f"File too large. Max size: {MAX_IMAGE_SIZE / (1024 * 1024):.1f}MB"
        )

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return file_path, content


async def detect_person(
    image_data: bytes,
    db: Session,
    engine_name: str | None = None,
    api_key_id: int | None = None,
) -> DetectionResponse:
    """
    Detect a person in an image.

    Args:
        image_data: Raw image bytes
        db: Database session
        engine_name: Specific engine to use (default if None)
        api_key_id: ID of API key making the request (for logging)

    Returns:
        DetectionResponse with person info or queued status
    """
    # Get detection engine
    engine = EngineRegistry.get_engine(engine_name)
    if not engine:
        raise ValueError(f"Engine '{engine_name}' not found")

    # Perform detection
    result = await engine.detect(image_data, db)

    # Log the detection
    detection_log = DetectionLog(
        image_path="inline",  # Will update if we save
        detected_person_id=result.person_id,
        confidence=result.confidence,
        engine_used=engine.name,
        api_key_id=api_key_id,
    )
    db.add(detection_log)
    db.flush()  # Get ID

    if result.matched:
        # Found a match
        db.commit()
        return DetectionResponse(
            person=result.person_name,
            person_id=result.person_id,
            confidence=result.confidence,
            queued_for_annotation=False,
            engine_used=engine.name,
        )
    else:
        # No match - add to annotation queue
        # Save the image for annotation
        filename = f"unknown_{detection_log.id}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = UPLOAD_DIR / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(image_data)

        detection_log.image_path = filename  # type: ignore[assignment]

        import json
        queue_item = AnnotationQueue(
            detection_log_id=detection_log.id,
            image_path=filename,
            status="pending",
            box_2d=json.dumps(result.box) if result.box else None,
        )
        db.add(queue_item)
        db.commit()

        return DetectionResponse(
            person=None,
            person_id=None,
            confidence=0.0,
            queued_for_annotation=True,
            engine_used=engine.name,
        )


async def add_reference_image(
    person_id: int,
    image_data: bytes,
    db: Session,
    engine_name: str | None = None,
) -> ReferenceImage:
    """
    Add a reference image for a person.

    Args:
        person_id: Person ID
        image_data: Raw image bytes
        db: Database session
        engine_name: Engine to use for embedding

    Returns:
        Created ReferenceImage
    """
    engine = EngineRegistry.get_engine(engine_name)
    if not engine:
        raise ValueError(f"Engine '{engine_name}' not found")

    # Save image file
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise ValueError(f"Person {person_id} not found")

    filename = f"ref_{person_id}_{uuid.uuid4().hex[:8]}.jpg"
    file_path = UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(image_data)

    # Compute embedding
    embedding = await engine.compute_embedding(image_data)

    # Create reference image record
    ref_image = ReferenceImage(
        person_id=person_id,
        image_path=filename,
        embedding=embedding,
        engine_type=engine.name,
    )
    db.add(ref_image)
    db.commit()
    db.refresh(ref_image)

    return ref_image
