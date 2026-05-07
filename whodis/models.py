"""SQLAlchemy models for WhoDis."""

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from whodis.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class User(Base):
    """Admin users for web interface."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    api_keys = relationship("APIKey", back_populates="created_by_user")
    annotations = relationship("AnnotationQueue", back_populates="annotated_by_user")


class APIKey(Base):
    """API keys for client authentication."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    key_hash = Column(String, unique=True, nullable=False)  # SHA256 hash of key
    name = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    created_by_user = relationship("User", back_populates="api_keys")
    detection_logs = relationship("DetectionLog", back_populates="api_key")


class Person(Base):
    """Known persons in the system."""

    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    reference_images = relationship(
        "ReferenceImage", back_populates="person", cascade="all, delete-orphan"
    )
    detection_logs = relationship("DetectionLog", back_populates="detected_person")
    annotation_suggestions = relationship(
        "AnnotationQueue",
        foreign_keys="AnnotationQueue.suggested_person_id",
        back_populates="suggested_person",
    )


class ReferenceImage(Base):
    """Reference face images for each person."""

    __tablename__ = "reference_images"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    image_path = Column(String, nullable=False)
    embedding = Column(LargeBinary, nullable=True)  # Precomputed embedding
    engine_type = Column(String, nullable=True)  # Which engine generated this embedding
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    person = relationship("Person", back_populates="reference_images")

    @property
    def image_url(self) -> str:
        """Get the web URL for the image."""
        if not self.image_path:
            return ""
        if "/" in self.image_path or "\\" in self.image_path:
            return f"/uploads/{Path(self.image_path).name}"
        return f"/uploads/{self.image_path}"

    @property
    def full_image_path(self) -> Path:
        """Get the absolute path for file operations."""
        from whodis.config import UPLOAD_DIR

        if not self.image_path:
            return Path("")
        if Path(self.image_path).is_absolute():
            return Path(self.image_path)
        return UPLOAD_DIR / self.image_path


class DetectionLog(Base):
    """Log of all detection attempts."""

    __tablename__ = "detection_logs"

    id = Column(Integer, primary_key=True)
    image_path = Column(String, nullable=False)
    detected_person_id = Column(Integer, ForeignKey("people.id"), nullable=True)
    confidence = Column(Float, nullable=True)
    engine_used = Column(String, nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    detected_person = relationship("Person", back_populates="detection_logs")
    api_key = relationship("APIKey", back_populates="detection_logs")
    annotation_queue = relationship("AnnotationQueue", back_populates="detection_log")


class AnnotationQueue(Base):
    """Queue of unknown detections pending annotation."""

    __tablename__ = "annotation_queue"

    id = Column(Integer, primary_key=True)
    detection_log_id = Column(Integer, ForeignKey("detection_logs.id"), nullable=False)
    image_path = Column(String, nullable=False)
    suggested_person_id = Column(Integer, ForeignKey("people.id"), nullable=True)
    status = Column(String, default="pending")  # pending, annotated, ignored
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    @property
    def image_url(self) -> str:
        """Get the web URL for the image."""
        if not self.image_path:
            return ""
        # Handle both absolute paths and filenames
        if "/" in self.image_path or "\\" in self.image_path:
            return f"/uploads/{Path(self.image_path).name}"
        return f"/uploads/{self.image_path}"

    @property
    def full_image_path(self) -> Path:
        """Get the absolute path for file operations."""
        from whodis.config import UPLOAD_DIR

        if not self.image_path:
            return Path("")
        if Path(self.image_path).is_absolute():
            return Path(self.image_path)
        return UPLOAD_DIR / self.image_path

    annotated_at = Column(DateTime, nullable=True)
    annotated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    detection_log = relationship("DetectionLog", back_populates="annotation_queue")
    suggested_person = relationship(
        "Person",
        foreign_keys=[suggested_person_id],
        back_populates="annotation_suggestions",
    )
    annotated_by_user = relationship("User", back_populates="annotations")


# Database setup
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
