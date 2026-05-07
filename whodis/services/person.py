"""Person management service."""

from sqlalchemy.orm import Session

from whodis.models import Person, ReferenceImage
from whodis.schemas import PersonCreate, PersonUpdate


def get_person_by_id(db: Session, person_id: int) -> Person | None:
    """Get a person by ID."""
    return db.query(Person).filter(Person.id == person_id).first()


def get_person_by_name(db: Session, name: str) -> Person | None:
    """Get a person by name (case-insensitive)."""
    return db.query(Person).filter(Person.name.ilike(name)).first()


def list_people(db: Session, skip: int = 0, limit: int = 100) -> list[Person]:
    """List all people with pagination."""
    return db.query(Person).order_by(Person.name).offset(skip).limit(limit).all()


def create_person(db: Session, data: PersonCreate) -> Person:
    """Create a new person."""
    person = Person(name=data.name, notes=data.notes or "")
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update_person(db: Session, person_id: int, data: PersonUpdate) -> Person | None:
    """Update a person's details."""
    person = get_person_by_id(db, person_id)
    if not person:
        return None

    if data.name is not None:
        person.name = data.name
    if data.notes is not None:
        person.notes = data.notes

    db.commit()
    db.refresh(person)
    return person


def delete_person(db: Session, person_id: int) -> bool:
    """Delete a person and their reference images."""
    person = get_person_by_id(db, person_id)
    if not person:
        return False

    db.delete(person)
    db.commit()
    return True


def get_person_reference_images(db: Session, person_id: int) -> list[ReferenceImage]:
    """Get all reference images for a person."""
    return (
        db.query(ReferenceImage)
        .filter(ReferenceImage.person_id == person_id)
        .order_by(ReferenceImage.created_at.desc())
        .all()
    )


def count_people(db: Session) -> int:
    """Get total count of people."""
    return db.query(Person).count()


def search_people(db: Session, query: str, limit: int = 10) -> list[Person]:
    """Search people by name."""
    return db.query(Person).filter(Person.name.ilike(f"%{query}%")).limit(limit).all()
