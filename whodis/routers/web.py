"""Web routes for the annotation interface."""

from datetime import UTC

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from whodis.auth import require_admin
from whodis.config import BASE_DIR, DEFAULT_ENGINE
from whodis.engines.registry import EngineRegistry
from whodis.models import AnnotationQueue, ReferenceImage, User, get_db
from whodis.schemas import AnnotationSubmit, PersonCreate
from whodis.services.annotation import (
    get_annotation_stats,
    get_pending_annotations,
    submit_annotation,
)
from whodis.services.detection import add_reference_image
from whodis.services.person import (
    count_people,
    create_person,
    delete_person,
    get_person_by_id,
    get_person_reference_images,
    list_people,
)

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    """Main dashboard page."""
    from datetime import datetime, timedelta

    from whodis.models import APIKey, DetectionLog

    stats = {
        "total_people": count_people(db),
        "total_reference_images": db.query(ReferenceImage).count(),
        "pending_annotations": db.query(AnnotationQueue)
        .filter(AnnotationQueue.status == "pending")
        .count(),
        "total_detections_24h": db.query(DetectionLog)
        .filter(
            DetectionLog.created_at
            >= datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
        )
        .count(),
        "api_keys_count": db.query(APIKey).filter(APIKey.created_by == user.id).count(),
    }

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "stats": stats},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(request, "login.html", {})


@router.get("/people", response_class=HTMLResponse)
async def people_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    """List all people."""
    people = list_people(db)

    # Add reference image count for each
    for person in people:
        person.reference_image_count = (  # type: ignore[attr-defined]
            db.query(ReferenceImage)
            .filter(ReferenceImage.person_id == person.id)
            .count()
        )

    # Get available engines
    available_engines = EngineRegistry.list_engines()

    return templates.TemplateResponse(
        request,
        "people.html",
        {
            "user": user,
            "people": people,
            "available_engines": available_engines,
            "default_engine": DEFAULT_ENGINE,
        },
    )


@router.get("/people/{person_id}", response_class=HTMLResponse)
async def person_detail(
    person_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    """Person detail page."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    reference_images = get_person_reference_images(db, person_id)

    # Get available engines
    available_engines = EngineRegistry.list_engines()

    return templates.TemplateResponse(
        request,
        "person_detail.html",
        {
            "user": user,
            "person": person,
            "reference_images": reference_images,
            "available_engines": available_engines,
            "default_engine": DEFAULT_ENGINE,
        },
    )


@router.post("/people")
async def create_person_form(
    request: Request,
    name: str = Form(...),
    notes: str = Form(""),
    image: UploadFile = File(None),
    engine: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    """Create a new person."""
    data = PersonCreate(name=name, notes=notes)
    person = create_person(db, data)

    # If image uploaded, add as reference
    if image and image.filename:
        image_data = await image.read()
        await add_reference_image(person.id, image_data, db, engine_name=engine)  # type: ignore[arg-type]

    return RedirectResponse(url="/people", status_code=status.HTTP_302_FOUND)


@router.post("/people/{person_id}/delete")
async def delete_person_form(
    person_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    """Delete a person."""
    delete_person(db, person_id)
    return RedirectResponse(url="/people", status_code=status.HTTP_302_FOUND)


@router.post("/people/{person_id}/add-image")
async def add_person_image(
    person_id: int,
    image: UploadFile = File(...),
    engine: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    """Add a reference image to a person."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    image_data = await image.read()
    await add_reference_image(person.id, image_data, db, engine_name=engine)  # type: ignore[arg-type]

    return RedirectResponse(
        url=f"/people/{person_id}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/annotate", response_class=HTMLResponse)
async def annotation_queue(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    """Annotation queue page."""
    pending = get_pending_annotations(db)
    stats = get_annotation_stats(db)

    # Get all people for the dropdown
    people = list_people(db)

    # Get available engines
    available_engines = EngineRegistry.list_engines()

    return templates.TemplateResponse(
        request,
        "annotate.html",
        {
            "user": user,
            "pending": pending,
            "stats": stats,
            "people": people,
            "available_engines": available_engines,
            "default_engine": DEFAULT_ENGINE,
        },
    )


@router.post("/annotate/{annotation_id}")
async def submit_annotation_form(
    annotation_id: int,
    request: Request,
    person_id: str | None = Form(None),
    new_person_name: str = Form(""),
    ignore: str = Form(""),
    engine: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    """Submit an annotation."""
    data = AnnotationSubmit(
        person_id=int(person_id) if person_id and person_id.strip() else None,
        new_person_name=new_person_name.strip() or None,
        ignore=ignore.lower() == "true",
        engine=engine or None,
    )

    await submit_annotation(annotation_id, data, user.id, db)  # type: ignore[arg-type]

    return RedirectResponse(url="/annotate", status_code=status.HTTP_302_FOUND)


@router.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    """API keys management page."""
    from whodis.models import APIKey

    keys = db.query(APIKey).filter(APIKey.created_by == user.id).all()

    return templates.TemplateResponse(
        request,
        "api_keys.html",
        {"user": user, "keys": keys},
    )
