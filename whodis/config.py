"""Configuration settings for WhoDis."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# Data Directory
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/whodis.db")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# Admin defaults
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Detection engine
DEFAULT_ENGINE = os.getenv("DEFAULT_ENGINE", "imagehash")

# File storage
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", DATA_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 10 * 1024 * 1024))  # 10MB

# Image processing
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", 1024))
SUPPORTED_IMAGE_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "GIF", "BMP"}

# Detection thresholds
IMAGEHASH_THRESHOLD = int(os.getenv("IMAGEHASH_THRESHOLD", 10))
