# WhoDis - Person Detection API

A FastAPI-based person detection system with web annotation interface.

## Features

- **Modular Detection Engines**: Pluggable architecture supporting multiple backends (ImageHash default)
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
