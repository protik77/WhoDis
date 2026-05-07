"""Annotation service for managing the annotation queue."""

from datetime import datetime

from sqlalchemy.orm import Session

from whodis.models import AnnotationQueue, DetectionLog, Person
from whodis.schemas import AnnotationSubmit


def get_pending_annotations(db: Session, limit: int = 50) -> list[AnnotationQueue]:
    """Get pending annotation queue items."""
    return (
        db.query(AnnotationQueue)
        .filter(AnnotationQueue.status == "pending")
        .order_by(AnnotationQueue.created_at.desc())
        .limit(limit)
        .all()
    )


def get_annotation_by_id(db: Session, annotation_id: int) -> AnnotationQueue | None:
    """Get a specific annotation queue item."""
    return db.query(AnnotationQueue).filter(AnnotationQueue.id == annotation_id).first()


def get_annotation_stats(db: Session) -> dict:
    """Get annotation queue statistics."""
    pending = (
        db.query(AnnotationQueue).filter(AnnotationQueue.status == "pending").count()
    )
    annotated = (
        db.query(AnnotationQueue).filter(AnnotationQueue.status == "annotated").count()
    )
    ignored = (
        db.query(AnnotationQueue).filter(AnnotationQueue.status == "ignored").count()
    )

    return {
        "pending": pending,
        "annotated": annotated,
        "ignored": ignored,
        "total": pending + annotated + ignored,
    }


async def submit_annotation(
    annotation_id: int,
    data: AnnotationSubmit,
    annotated_by: int,
    db: Session,
) -> dict:
    """
    Submit an annotation for an unknown detection.

    Args:
        annotation_id: ID of the annotation queue item
        data: Annotation data (person_id, new_person_name, or ignore)
        annotated_by: User ID who is annotating
        db: Database session

    Returns:
        Result info
    """
    queue_item = get_annotation_by_id(db, annotation_id)
    if not queue_item:
        raise ValueError(f"Annotation {annotation_id} not found")

    if queue_item.status != "pending":
        raise ValueError(f"Annotation {annotation_id} is not pending")

    if data.ignore:
        # Mark as ignored
        queue_item.status = "ignored"
        queue_item.annotated_at = datetime.utcnow()
        queue_item.annotated_by = annotated_by
        db.commit()
        return {"action": "ignored", "annotation_id": annotation_id}

    # Determine person
    person = None
    if data.new_person_name:
        # Create new person
        person = Person(name=data.new_person_name, notes="")
        db.add(person)
        db.flush()
    elif data.person_id:
        # Use existing person
        person = db.query(Person).filter(Person.id == data.person_id).first()
        if not person:
            raise ValueError(f"Person {data.person_id} not found")
    else:
        raise ValueError("Must provide person_id or new_person_name")

    # Read image data
    import aiofiles

    async with aiofiles.open(queue_item.image_path, "rb") as f:
        image_data = await f.read()

    # Add as reference image
    from whodis.services.detection import add_reference_image as add_ref

    ref_image = await add_ref(
        person_id=person.id,
        image_data=image_data,
        db=db,
    )

    # Update queue item
    queue_item.status = "annotated"
    queue_item.suggested_person_id = person.id
    queue_item.annotated_at = datetime.utcnow()
    queue_item.annotated_by = annotated_by

    # Update detection log
    detection_log = (
        db.query(DetectionLog)
        .filter(DetectionLog.id == queue_item.detection_log_id)
        .first()
    )
    if detection_log:
        detection_log.detected_person_id = person.id
        detection_log.confidence = 1.0  # Human verified

    db.commit()

    return {
        "action": "annotated",
        "annotation_id": annotation_id,
        "person_id": person.id,
        "person_name": person.name,
        "reference_image_id": ref_image.id,
    }
