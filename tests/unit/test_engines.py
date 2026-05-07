"""Unit tests for detection engines."""

import io
import pytest
from PIL import Image

from whodis.engines.imagehash_engine import ImageHashEngine
from whodis.engines.registry import EngineRegistry


class TestImageHashEngine:
    """Test ImageHash engine functionality."""

    def test_engine_name(self):
        """Test engine has correct name."""
        engine = ImageHashEngine()
        assert engine.name == "imagehash"

    def test_compute_embedding(self):
        """Test embedding computation."""
        engine = ImageHashEngine()
        
        # Create a test image
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        
        # Compute embedding
        embedding = engine.compute_embedding(img_bytes.getvalue())
        
        assert embedding is not None
        assert len(embedding) > 0

    def test_compare_embeddings_same_image(self):
        """Test comparing embeddings of the same image."""
        engine = ImageHashEngine()
        
        # Create a test image
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        
        # Compute embedding twice
        emb1 = engine.compute_embedding(img_bytes.getvalue())
        
        img_bytes.seek(0)
        emb2 = engine.compute_embedding(img_bytes.getvalue())
        
        # Compare
        similarity = engine.compare_embeddings(emb1, emb2)
        
        assert similarity > 0.99  # Should be nearly identical

    def test_compare_embeddings_different_images(self):
        """Test comparing embeddings of different images."""
        engine = ImageHashEngine()
        
        # Create two different images
        img1 = Image.new("RGB", (100, 100), color="red")
        img2 = Image.new("RGB", (100, 100), color="blue")
        
        buf1 = io.BytesIO()
        buf2 = io.BytesIO()
        img1.save(buf1, format="JPEG")
        img2.save(buf2, format="JPEG")
        
        emb1 = engine.compute_embedding(buf1.getvalue())
        emb2 = engine.compute_embedding(buf2.getvalue())
        
        # Compare
        similarity = engine.compare_embeddings(emb1, emb2)
        
        assert similarity < 0.9  # Should be less similar

    def test_resize_large_image(self):
        """Test that large images are resized."""
        engine = ImageHashEngine()
        
        # Create a large image
        img = Image.new("RGB", (2000, 2000), color="green")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        
        # Compute embedding (should not error)
        embedding = engine.compute_embedding(img_bytes.getvalue())
        
        assert embedding is not None


class TestEngineRegistry:
    """Test engine registry functionality."""

    def test_get_default_engine(self):
        """Test getting default engine."""
        engine = EngineRegistry.get_engine()
        
        assert engine is not None
        assert engine.name == "imagehash"

    def test_get_specific_engine(self):
        """Test getting a specific engine by name."""
        engine = EngineRegistry.get_engine("imagehash")
        
        assert engine is not None
        assert engine.name == "imagehash"

    def test_get_invalid_engine(self):
        """Test getting an invalid engine."""
        engine = EngineRegistry.get_engine("nonexistent")
        
        assert engine is None

    def test_list_engines(self):
        """Test listing available engines."""
        engines = EngineRegistry.list_engines()
        
        assert "imagehash" in engines
