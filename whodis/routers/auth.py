"""Authentication routes for web interface."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from whodis.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_default_admin,
    require_admin,
    verify_password,
)
from whodis.models import APIKey, User, get_db
from whodis.schemas import (
    APIKeyResponse,
    UserResponse,
)
from whodis.auth import generate_api_key, hash_api_key

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Login for web interface (session-based)."""
    # Find user
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Create session token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    # Set cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="session",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Logout and clear session."""
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session")
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(require_admin)):
    """Get current user info."""
    return current_user


# ==================== API Key Management ====================

@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all API keys."""
    keys = db.query(APIKey).filter(APIKey.created_by == current_user.id).all()
    return keys


@router.post("/api-keys")
async def create_api_key(
    request: Request,
    name: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new API key."""
    # Generate key
    key = generate_api_key()
    key_hash = hash_api_key(key)
    
    # Store in database
    api_key = APIKey(
        key_hash=key_hash,
        name=name,
        created_by=current_user.id,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # Show key in a simple HTML page since it's only shown once
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Key Created - WhoDis</title>
        <style>
            body {{ font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .key {{ background: #f4f4f4; padding: 15px; border-radius: 5px; font-family: monospace; word-break: break-all; }}
            .warning {{ color: #c33; background: #fee; padding: 10px; border-radius: 5px; margin: 20px 0; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>API Key Created</h1>
        <div class="warning">
            <strong>Important:</strong> This is the only time you will see this key. Copy it now!
        </div>
        <p><strong>Name:</strong> {name or 'Unnamed'}</p>
        <p><strong>Key:</strong></p>
        <div class="key">{key}</div>
        <p style="margin-top: 20px;">
            <a href="/api-keys" class="btn">Back to API Keys</a>
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Revoke an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.created_by == current_user.id,
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    api_key.is_active = False
    db.commit()
    
    return RedirectResponse(url="/api-keys", status_code=status.HTTP_302_FOUND)


@router.post("/init")
async def init_admin(db: Session = Depends(get_db)):
    """Initialize default admin (development only)."""
    # Check if any users exist
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin already initialized",
        )
    
    create_default_admin()
    return {"message": "Default admin created"}
