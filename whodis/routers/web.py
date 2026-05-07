"""Web routes for the annotation interface."""

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
from whodis.config import BASE_DIR
from whodis.models import AnnotationQueue, ReferenceImage, get_db
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
    user=Depends(require_admin),
):
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
        .filter(DetectionLog.created_at >= datetime.utcnow() - timedelta(hours=24))
        .count(),
        "api_keys_count": db.query(APIKey).filter(APIKey.created_by == user.id).count(),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "stats": stats},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/people", response_class=HTMLResponse)
async def people_list(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """List all people."""
    people = list_people(db)

    # Add reference image count for each
    for person in people:
        person.reference_image_count = (
            db.query(ReferenceImage)
            .filter(ReferenceImage.person_id == person.id)
            .count()
        )

    return templates.TemplateResponse(
        "people.html",
        {"request": request, "user": user, "people": people},
    )


@router.get("/people/{person_id}", response_class=HTMLResponse)
async def person_detail(
    person_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Person detail page."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    reference_images = get_person_reference_images(db, person_id)

    return templates.TemplateResponse(
        "person_detail.html",
        {
            "request": request,
            "user": user,
            "person": person,
            "reference_images": reference_images,
        },
    )


@router.post("/people")
async def create_person_form(
    request: Request,
    name: str = Form(...),
    notes: str = Form(""),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Create a new person."""
    data = PersonCreate(name=name, notes=notes)
    person = create_person(db, data)

    # If image uploaded, add as reference
    if image and image.filename:
        image_data = await image.read()
        await add_reference_image(person.id, image_data, db)

    return RedirectResponse(url="/people", status_code=status.HTTP_302_FOUND)


@router.post("/people/{person_id}/delete")
async def delete_person_form(
    person_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Delete a person."""
    delete_person(db, person_id)
    return RedirectResponse(url="/people", status_code=status.HTTP_302_FOUND)


@router.post("/people/{person_id}/add-image")
async def add_person_image(
    person_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Add a reference image to a person."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    image_data = await image.read()
    await add_reference_image(person.id, image_data, db)

    return RedirectResponse(
        url=f"/people/{person_id}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/annotate", response_class=HTMLResponse)
async def annotation_queue(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Annotation queue page."""
    pending = get_pending_annotations(db)
    stats = get_annotation_stats(db)

    # Get all people for the dropdown
    people = list_people(db)

    return templates.TemplateResponse(
        "annotate.html",
        {
            "request": request,
            "user": user,
            "pending": pending,
            "stats": stats,
            "people": people,
        },
    )


@router.post("/annotate/{annotation_id}")
async def submit_annotation_form(
    annotation_id: int,
    request: Request,
    person_id: int = Form(None),
    new_person_name: str = Form(None),
    ignore: bool = Form(False),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Submit an annotation."""
    data = AnnotationSubmit(
        person_id=person_id,
        new_person_name=new_person_name or None,
        ignore=ignore,
    )

    await submit_annotation(annotation_id, data, user.id, db)

    return RedirectResponse(url="/annotate", status_code=status.HTTP_302_FOUND)


@router.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """API keys management page."""
    from whodis.models import APIKey

    keys = db.query(APIKey).filter(APIKey.created_by == user.id).all()

    return templates.TemplateResponse(
        "api_keys.html",
        {"request": request, "user": user, "keys": keys},
    )
