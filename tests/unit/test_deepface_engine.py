"""Unit tests for DeepFace detection engine."""

import io
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from whodis.engines.registry import EngineRegistry


class TestDeepFaceEngine:
    """Test DeepFace engine functionality."""

    @pytest.fixture
    def mock_deepface(self) -> Generator[MagicMock, None, None]:
        """Create a mock for DeepFace module."""
        with patch("deepface.DeepFace", create=True) as mock:
            yield mock

    def test_engine_name(self, mock_deepface: MagicMock) -> None:
        """Test engine has correct name."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        engine = DeepFaceEngine()
        assert engine.name == "deepface"

    def test_default_configuration(self, mock_deepface: MagicMock) -> None:
        """Test default backend and model configuration."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        engine = DeepFaceEngine()
        assert engine.backend == "opencv"
        assert engine.model == "Facenet"

    def test_custom_configuration(self, mock_deepface: MagicMock) -> None:
        """Test custom backend and model configuration."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        engine = DeepFaceEngine(backend="dlib", model="Facenet512")
        assert engine.backend == "dlib"
        assert engine.model == "Facenet512"

    def test_invalid_backend_raises(self, mock_deepface: MagicMock) -> None:
        """Test invalid backend raises ValueError."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        with pytest.raises(ValueError, match="Invalid backend"):
            DeepFaceEngine(backend="invalid_backend")

    def test_invalid_model_raises(self, mock_deepface: MagicMock) -> None:
        """Test invalid model raises ValueError."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        with pytest.raises(ValueError, match="Invalid model"):
            DeepFaceEngine(model="invalid_model")

    @pytest.mark.asyncio
    async def test_compute_embedding_success(self, mock_deepface: MagicMock) -> None:
        """Test successful embedding computation."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        # Mock DeepFace.represent return value
        mock_embedding = np.random.randn(128).tolist()
        mock_deepface.represent.return_value = [{"embedding": mock_embedding}]

        engine = DeepFaceEngine()
        embedding = await engine.compute_embedding(img_bytes.getvalue())

        assert embedding is not None
        assert len(embedding) > 0

        # Verify DeepFace was called correctly
        mock_deepface.represent.assert_called_once()
        call_args = mock_deepface.represent.call_args
        assert call_args.kwargs["model_name"] == "Facenet"
        assert call_args.kwargs["detector_backend"] == "opencv"

    @pytest.mark.asyncio
    async def test_compute_embedding_no_face(self, mock_deepface: MagicMock) -> None:
        """Test embedding computation when no face detected."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        # Mock empty result (no faces)
        mock_deepface.represent.return_value = []

        engine = DeepFaceEngine()
        with pytest.raises(ValueError, match="No face detected"):
            await engine.compute_embedding(img_bytes.getvalue())

    def test_compare_embeddings_identical(self, mock_deepface: MagicMock) -> None:
        """Test comparing identical embeddings."""
        import pickle

        from whodis.engines.deepface_engine import DeepFaceEngine

        embedding = np.random.randn(128).astype(np.float32)
        emb_bytes = pickle.dumps(embedding)

        engine = DeepFaceEngine()
        similarity = engine.compare_embeddings(emb_bytes, emb_bytes)

        # Same embedding should have high similarity (near 1.0 after normalization)
        assert similarity > 0.99

    def test_compare_embeddings_different(self, mock_deepface: MagicMock) -> None:
        """Test comparing different embeddings."""
        import pickle

        from whodis.engines.deepface_engine import DeepFaceEngine

        emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        emb2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        engine = DeepFaceEngine()
        similarity = engine.compare_embeddings(pickle.dumps(emb1), pickle.dumps(emb2))

        # Orthogonal vectors should have 0.5 similarity after normalization from [-1,1] to [0,1]
        assert 0.4 <= similarity <= 0.6

    def test_compare_embeddings_invalid_data(self, mock_deepface: MagicMock) -> None:
        """Test comparing invalid embedding data."""
        from whodis.engines.deepface_engine import DeepFaceEngine

        engine = DeepFaceEngine()
        similarity = engine.compare_embeddings(b"invalid", b"invalid")

        assert similarity == 0.0


class TestEngineRegistration:
    """Test DeepFace engine registration."""

    def test_deepface_registered_if_available(self) -> None:
        """Test DeepFace engine is registered when dependencies available."""
        engines = EngineRegistry.list_engines()

        # DeepFace should be registered if we got here (dependencies installed)
        try:
            import deepface  # noqa: F401

            assert "deepface" in engines
        except ImportError:
            # If deepface not available, it shouldn't be registered
            assert "deepface" not in engines

    def test_get_deepface_engine(self) -> None:
        """Test getting DeepFace engine from registry."""
        try:
            import deepface  # noqa: F401

            engine = EngineRegistry.get_engine("deepface")
            assert engine is not None
            assert engine.name == "deepface"
        except ImportError:
            pytest.skip("DeepFace not installed")

    def test_imagehash_still_available(self) -> None:
        """Test ImageHash engine is still available."""
        engines = EngineRegistry.list_engines()
        assert "imagehash" in engines

        engine = EngineRegistry.get_engine("imagehash")
        assert engine is not None
        assert engine.name == "imagehash"
