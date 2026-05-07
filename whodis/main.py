"""WhoDis - Person Detection API with Web Annotation Interface."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from whodis.auth import create_default_admin
from whodis.config import BASE_DIR, UPLOAD_DIR
from whodis.models import init_db
from whodis.routers import api, auth, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    create_default_admin()
    yield
    # Shutdown


app = FastAPI(
    title="WhoDis",
    description="Person detection API with web annotation interface",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(web.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "whodis"}


def main():
    """Entry point for running the server."""
    import uvicorn

    uvicorn.run(
        "whodis.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
