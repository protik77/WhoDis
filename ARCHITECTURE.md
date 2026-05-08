# WhoDis Architecture and Implementation

This document provides a detailed overview of the architecture and implementation of WhoDis, a person detection API with a web annotation interface.

## 1. Overview

WhoDis is designed to be a lightweight, extensible system for person detection and identification. It allows clients (like Home Assistant or smart cameras) to submit images via API and receive the identity of the person in the image. If the person is unknown, the image is queued for human annotation via a web interface.

## 2. Technology Stack

*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) for high-performance async API and web routes.
*   **Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with [SQLite](https://www.sqlite.org/) for persistent storage.
*   **Dependency Management**: [uv](https://github.com/astral-sh/uv) for fast and reliable package management.
*   **Validation**: [Pydantic V2](https://docs.pydantic.dev/) for request/response schema validation.
*   **Templating**: [Jinja2](https://palletsprojects.com/p/jinja/) for the administrative web interface.
*   **Image Processing**: [Pillow](https://python-pillow.org/) and [ImageHash](https://github.com/JohannesBuchner/imagehash) for perceptual hashing.
*   **Security**: [bcrypt](https://github.com/pyca/bcrypt) for password hashing and [python-jose](https://github.com/mpdavis/python-jose) for JWT tokens.

## 3. Project Structure

```text
whodis/
├── engines/           # Pluggable detection engine implementations
│   ├── base.py        # Abstract base class for engines
│   ├── imagehash_engine.py # Perceptual hashing implementation
│   └── deepface_engine.py  # DeepFace face recognition implementation
├── services/          # Business logic and database operations
│   ├── annotation.py  # Management of unknown detections
│   ├── detection.py   # Core detection flow coordination
│   └── person.py      # CRUD for known identities
├── routers/           # FastAPI route definitions
│   ├── api.py         # External REST API
│   ├── auth.py        # Session and API key management
│   └── web.py         # Administrative web interface
├── models.py          # SQLAlchemy database models
├── schemas.py         # Pydantic validation schemas
├── auth.py            # Authentication and security utilities
├── config.py          # Environment configuration
└── main.py            # Application entry point and lifespan
```

## 4. Core Components

### Detection Engines
WhoDis uses a pluggable engine architecture. Any engine that inherits from `DetectionEngine` in `whodis/engines/base.py` can be used for identification. The default `ImageHashEngine` uses perceptual hashing to compare images against a library of reference images.

### Services Layer
Business logic is encapsulated in the `services/` directory. This separates the API/web layer from the underlying data operations, making the codebase easier to test and maintain.

### Authentication System
The system supports two types of authentication:
1.  **Session-based (JWT)**: Used for the administrative web interface.
2.  **API Keys**: Secure, long-lived keys for client integrations.

Authentication is enforced using FastAPI's dependency injection system (`require_auth`, `require_admin`, `require_api_key`).

## 5. Implementation Details

### Database Management
The application uses SQLAlchemy 2.0 with the `DeclarativeBase` pattern. Database sessions are managed via a generator dependency (`get_db`), ensuring clean connection handling and easy overriding in tests.

### Lifespan and Initialization
The application uses the FastAPI `lifespan` handler to initialize the database and create a default admin user upon startup if no users exist.

### Testing Strategy
The project maintains a comprehensive test suite using `pytest` and `pytest-asyncio`. Tests are divided into:
*   **Unit Tests**: Testing individual components in isolation.
*   **Integration Tests**: Testing the full API/Web flow using `TestClient`.

## 6. Development Workflow

The project leverages `make` as a task runner to simplify common development operations:

*   `make run`: Starts the FastAPI server with auto-reload.
*   `make test`: Runs the test suite with coverage reporting.
*   `make lint`: Runs `ruff` for formatting/linting and `mypy` for static type checking.
*   `make build-docker`: Containerizes the application for deployment.
