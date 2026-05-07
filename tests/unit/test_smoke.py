"""Smoke tests to ensure basic app functionality and prevent import regressions."""


def test_app_imports():
    """Verify that the FastAPI app can be imported without NameErrors or other issues."""
    from whodis.main import app

    assert app is not None


def test_models_import():
    """Verify that models can be imported and Path is defined."""
    from pathlib import Path

    from whodis.models import AnnotationQueue, ReferenceImage

    # Check that Path is used in type hints and is correctly imported
    assert ReferenceImage.full_image_path.fget.__annotations__["return"] == Path
    assert AnnotationQueue.full_image_path.fget.__annotations__["return"] == Path
