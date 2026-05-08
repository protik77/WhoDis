"""Base class for detection engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass
class DetectionResult:
    """Result of a detection attempt."""

    person_id: int | None
    person_name: str | None
    confidence: float  # 0.0 to 1.0
    matched: bool
    box: list[float] | None = None  # [x, y, w, h] as percentages


@dataclass
class ReferenceMatch:
    """A potential match from reference images."""

    person_id: int
    person_name: str
    reference_image_id: int
    similarity: float  # 0.0 to 1.0


class DetectionEngine(ABC):
    """Abstract base class for person detection engines."""

    name: str = "base"

    @abstractmethod
    async def detect(self, image_data: bytes, db_session: Session) -> DetectionResult:
        """
        Detect a person in an image.

        Args:
            image_data: Raw image bytes
            db_session: Database session for querying reference images

        Returns:
            DetectionResult with person info or None if no match
        """
        pass

    @abstractmethod
    async def compute_embedding(self, image_data: bytes) -> bytes:
        """
        Compute an embedding for an image.

        Args:
            image_data: Raw image bytes

        Returns:
            Binary embedding data
        """
        pass

    @abstractmethod
    def compare_embeddings(self, emb1: bytes, emb2: bytes) -> float:
        """
        Compare two embeddings and return similarity score.

        Args:
            emb1: First embedding
            emb2: Second embedding

        Returns:
            Similarity score (0.0 to 1.0, higher is more similar)
        """
        pass

    async def find_matches(
        self,
        image_data: bytes,
        db_session: Session,
        threshold: float = 0.8,
        embedding: bytes | None = None,
    ) -> list[ReferenceMatch]:
        """
        Find all potential matches above threshold.

        Args:
            image_data: Raw image bytes
            db_session: Database session
            threshold: Minimum similarity score (0.0 to 1.0)
            embedding: Optional precomputed embedding (to avoid recomputation)

        Returns:
            List of ReferenceMatch objects, sorted by similarity
        """
        query_embedding = (
            embedding
            if embedding is not None
            else await self.compute_embedding(image_data)
        )

        # Get all reference images with embeddings for this engine
        from whodis.models import Person, ReferenceImage

        refs = (
            db_session.query(ReferenceImage, Person)
            .join(Person, ReferenceImage.person_id == Person.id)
            .filter(
                ReferenceImage.embedding.isnot(None),
                ReferenceImage.engine_type == self.name,
            )
            .all()
        )

        matches = []
        for ref, person in refs:
            similarity = self.compare_embeddings(query_embedding, ref.embedding)
            if similarity >= threshold:
                matches.append(
                    ReferenceMatch(
                        person_id=person.id,
                        person_name=person.name,
                        reference_image_id=ref.id,
                        similarity=similarity,
                    )
                )

        # Sort by similarity, highest first
        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches
