# WhoDis - Person Detection API

A FastAPI-based person detection system with web annotation interface.

[Read the Architecture Documentation](ARCHITECTURE.md)

## Features

- **Modular Detection Engines**: Pluggable architecture supporting multiple backends (ImageHash default, DeepFace face recognition)
- **Web Annotation Interface**: Review unknown detections and assign identities
- **API for Clients**: REST API for Home Assistant and other integrations
- **API Key Authentication**: Secure key-based access for automation
- **SQLite Database**: Simple, file-based storage

## Quick Start

```bash
# Install dependencies
uv sync

# Run the application
make run
```

Default login: `admin` / `admin123` (Configurable via environment variables)

## Development

Useful commands for development:

```bash
# Run tests
make test

# Run linting and type checks
make lint

# Build Docker image
make build-docker
```

## API Usage

### Authentication
Use API keys via the `Authorization` header:

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "image=@/path/to/image.jpg" \
  http://localhost:8000/api/detect
```

### Detect Person

**POST /api/detect**

**Parameters:**
- `image` (file): Image to analyze
- `engine` (optional): Detection engine to use

**Response:**
```json
{
  "person": "John Doe",
  "person_id": 1,
  "confidence": 0.95,
  "queued_for_annotation": false,
  "engine_used": "imagehash"
}
```

If person is unknown:
```json
{
  "person": null,
  "person_id": null,
  "confidence": 0.0,
  "queued_for_annotation": true,
  "engine_used": "imagehash"
}
```

## Detection Engines

WhoDis supports multiple detection engines:

### ImageHash (Default)
Uses perceptual hashing for image similarity. Fast and simple, but not face-aware.

### DeepFace (Face Recognition)
True face recognition using DeepFace library with OpenCV backend. Optimized for CPU usage.

**Configuration** (via environment variables in `.env`):
```bash
# Set default engine
default_engine=deepface

# DeepFace settings (CPU optimized)
DEEPFACE_BACKEND=opencv        # opencv (fast), dlib (accurate), mtcnn, retinaface
DEEPFACE_MODEL=Facenet         # Facenet (128-dim, fast), Facenet512, VGG-Face
DEEPFACE_THRESHOLD=0.4         # Similarity threshold (0.0-1.0)
```

**Using Engines**:
```bash
# API: Explicitly select engine
curl -X POST \
  -H "Authorization: Bearer KEY" \
  -F "image=@photo.jpg" \
  -F "engine=deepface" \
  http://localhost:8000/api/detect

# Web UI: Select engine in annotation page dropdown
# Your choice is persisted via session storage
```

**Engine Comparison**:

| Feature | ImageHash | DeepFace |
|---------|-----------|----------|
| Face-aware | No | Yes |
| Rotation invariant | Partial | Yes |
| Lighting invariant | Partial | Yes |
| CPU Speed | Very fast | Fast |
| Accuracy | Good | Better |
| Best for | General objects | Faces |

## Project Structure

```
whodis/
├── engines/           # Detection engine implementations
├── services/          # Business logic
├── routers/           # API and web routes
├── templates/         # Jinja2 HTML templates
├── static/           # CSS/JS files
└── uploads/          # Stored images
```

## Architecture

1. **Detection Flow**:
   - Client submits image via API
   - Engine compares against reference images
   - Known: Return person name
   - Unknown: Queue for annotation

2. **Annotation Flow**:
   - Admin reviews pending images in web UI
   - Assign to existing or new person
   - Image becomes reference for future matches

3. **Engine System**:
   - Base class defines interface
   - ImageHash engine uses perceptual hashing
   - Easy to add new engines (face_recognition, YOLO, etc.)
