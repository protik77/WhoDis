"""Smoke tests to ensure basic app functionality and prevent import regressions."""


def test_app_imports() -> None:
    """Verify that the FastAPI app can be imported without NameErrors or other issues."""
    from whodis.main import app

    assert app is not None


def test_models_import() -> None:
    """Verify that models can be imported."""
    from whodis.models import AnnotationQueue, ReferenceImage

    assert ReferenceImage is not None
    assert AnnotationQueue is not None
