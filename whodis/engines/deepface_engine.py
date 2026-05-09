"""DeepFace-based detection engine for face recognition."""

import io
import pickle

import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from whodis.config import MAX_IMAGE_DIMENSION
from whodis.engines.base import DetectionEngine, DetectionResult


class DeepFaceEngine(DetectionEngine):
    """
    Detection engine using DeepFace for face recognition.

    Uses OpenCV backend with Facenet model by default for CPU efficiency.
    Supports configurable backend and model selection.
    """

    name = "deepface"

    def __init__(self, backend: str | None = None, model: str | None = None):
        """
        Initialize DeepFace engine.

        Args:
            backend: Face detection backend ('opencv', 'dlib', 'mtcnn', etc.)
                     Defaults to 'opencv' for CPU efficiency
            model: Face recognition model ('Facenet', 'Facenet512', 'VGG-Face', etc.)
                   Defaults to 'Facenet' for speed
        """
        import os

        from deepface import DeepFace

        self.DeepFace = DeepFace
        self.backend = backend or os.getenv("DEEPFACE_BACKEND", "opencv")
        self.model = model or os.getenv("DEEPFACE_MODEL", "Facenet")

        # Validate configuration
        valid_backends = ["opencv", "dlib", "mtcnn", "retinaface", "mediapipe"]
        valid_models = [
            "Facenet",
            "Facenet512",
            "VGG-Face",
            "OpenFace",
            "DeepFace",
            "ArcFace",
        ]

        if self.backend not in valid_backends:
            raise ValueError(
                f"Invalid backend '{self.backend}'. Valid: {valid_backends}"
            )
        if self.model not in valid_models:
            raise ValueError(f"Invalid model '{self.model}'. Valid: {valid_models}")

    def _load_image(self, image_data: bytes) -> np.ndarray:
        """Load image from bytes to numpy array (BGR format for OpenCV)."""
        from typing import cast

        img = cast(Image.Image, Image.open(io.BytesIO(image_data)))

        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if too large
        width, height = img.size
        max_dim = MAX_IMAGE_DIMENSION
        if width > max_dim or height > max_dim:
            ratio = min(max_dim / width, max_dim / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to numpy array (RGB)
        img_array = np.array(img)

        return img_array

    async def compute_embedding(self, image_data: bytes) -> bytes:
        """
        Compute face embedding for an image.

        Args:
            image_data: Raw image bytes

        Returns:
            Binary embedding data (pickled numpy array)
        """
        img_array = self._load_image(image_data)

        try:
            # Extract embedding using DeepFace
            embedding_objs = self.DeepFace.represent(
                img_path=img_array,
                model_name=self.model,
                detector_backend=self.backend,
                enforce_detection=True,  # Fail if no face detected
            )

            if not embedding_objs:
                raise ValueError("No face detected in image")

            # If multiple faces, take the first one (largest face usually comes first)
            embedding = embedding_objs[0]["embedding"]
            embedding_array = np.array(embedding, dtype=np.float32)

            # Serialize with pickle
            return pickle.dumps(embedding_array)

        except Exception as e:
            raise ValueError(f"Failed to compute embedding: {e}") from e

    def compare_embeddings(self, emb1: bytes, emb2: bytes) -> float:
        """
        Compare two face embeddings using cosine similarity.

        Args:
            emb1: First embedding (pickled numpy array)
            emb2: Second embedding (pickled numpy array)

        Returns:
            Similarity score (0.0 to 1.0, higher is more similar)
        """
        try:
            vec1 = pickle.loads(emb1)
            vec2 = pickle.loads(emb2)
        except Exception:
            return 0.0

        # Cosine similarity: dot(a, b) / (||a|| * ||b||)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cosine_sim = dot_product / (norm1 * norm2)

        # Convert from [-1, 1] to [0, 1] range
        # Cosine similarity ranges from -1 (opposite) to 1 (identical)
        similarity = (cosine_sim + 1.0) / 2.0

        return float(similarity)

    async def detect(self, image_data: bytes, db_session: Session) -> DetectionResult:
        """
        Detect a person using face recognition.

        Args:
            image_data: Raw image bytes
            db_session: Database session for querying reference images

        Returns:
            DetectionResult with person info or no match
        """
        from whodis.config import DEEPFACE_THRESHOLD

        threshold = float(DEEPFACE_THRESHOLD)

        try:
            # Get face embedding and detection box
            img_array = self._load_image(image_data)
            embedding_objs = self.DeepFace.represent(
                img_path=img_array,
                model_name=self.model,
                detector_backend=self.backend,
                enforce_detection=True,
            )

            if not embedding_objs:
                return DetectionResult(
                    person_id=None,
                    person_name=None,
                    confidence=0.0,
                    matched=False,
                    box=None,
                )

            results = []
            for face_data in embedding_objs:
                _query_embedding = pickle.dumps(
                    np.array(face_data["embedding"], dtype=np.float32)
                )

                box = None
                if "facial_area" in face_data:
                    area = face_data["facial_area"]
                    img_h, img_w = img_array.shape[:2]
                    box = [
                        (area["x"] / img_w) * 100,
                        (area["y"] / img_h) * 100,
                        (area["w"] / img_w) * 100,
                        (area["h"] / img_h) * 100,
                    ]

                matches = await self.find_matches(
                    image_data,
                    db_session,
                    threshold=threshold,
                    embedding=_query_embedding,
                )

                if not matches:
                    results.append(
                        DetectionResult(
                            person_id=None,
                            person_name=None,
                            confidence=0.0,
                            matched=False,
                            box=box,
                        )
                    )
                else:
                    best_match = matches[0]
                    results.append(
                        DetectionResult(
                            person_id=best_match.person_id,
                            person_name=best_match.person_name,
                            confidence=best_match.similarity,
                            matched=True,
                            box=box,
                        )
                    )

            return results

        except Exception:
            # No face detected or other error
            return [
                DetectionResult(
                    person_id=None,
                    person_name=None,
                    confidence=0.0,
                    matched=False,
                    box=None,
                )
            ]

    async def detect_faces(self, image_data: bytes) -> list[dict]:
        """
        Detect all faces in an image (utility method).

        Args:
            image_data: Raw image bytes

        Returns:
            List of face data dicts with embedding and location
        """
        img_array = self._load_image(image_data)

        try:
            from typing import Any, cast

            embedding_objs = self.DeepFace.represent(
                img_path=img_array,
                model_name=self.model,
                detector_backend=self.backend,
                enforce_detection=True,
            )
            return cast(list[dict[Any, Any]], embedding_objs)
        except Exception:
            return []
