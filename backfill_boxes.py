"""Backfill existing annotations with a default bounding box."""

import json

from whodis.models import AnnotationQueue, SessionLocal


def backfill():
    db = SessionLocal()
    try:
        pending = db.query(AnnotationQueue).filter(AnnotationQueue.box_2d is None).all()
        print(f"Found {len(pending)} annotations without boxes.")

        # Default box: [25, 25, 50, 50] - a 50% box in the center
        default_box = [25, 25, 50, 50]
        box_json = json.dumps(default_box)

        for item in pending:
            item.box_2d = box_json

        db.commit()
        print(f"Successfully backfilled {len(pending)} annotations.")
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
