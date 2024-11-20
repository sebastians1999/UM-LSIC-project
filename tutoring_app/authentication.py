from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter
from fastapi.security import OAuth2AuthorizationCodeBearer, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from typing import List
from database import UserRole
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from logger import logger  # Add this import
import httpx
import os
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError, jwt
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = [
    'SECRET_KEY',
    'TOKEN_EXPIRE_MINUTES',
    'REFRESH_TOKEN_EXPIRE_DAYS'
]

# Optional OAuth vars that will be set up interactively
oauth_env_vars = [
    'GITLAB_CLIENT_ID',
    'GITLAB_CLIENT_SECRET',
    'GITLAB_REDIRECT_URI',
    'GITLAB_BASE_URL',
]

for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Add OAuth2 scheme configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize app
router = APIRouter()

# Add rate limiting
limiter = Limiter(key_func=get_remote_address)

# Add OAuth configuration constants
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET")
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI")
GITLAB_BASE_URL = os.getenv("GITLAB_BASE_URL", "https://gitlab.com")

# Initialize OAuth only if credentials are available
oauth = None
gitlab = None
try:
    if all([GITLAB_CLIENT_ID, GITLAB_CLIENT_SECRET, GITLAB_REDIRECT_URI]):
        config = Config(environ={
            "GITLAB_CLIENT_ID": GITLAB_CLIENT_ID,
            "GITLAB_CLIENT_SECRET": GITLAB_CLIENT_SECRET,
            "GITLAB_SERVER_METADATA_URL": f"{GITLAB_BASE_URL}/.well-known/openid-configuration",
            "GITLAB_REDIRECT_URI": GITLAB_REDIRECT_URI,
        })
        
        oauth = OAuth(config)
        gitlab = oauth.register(
            name="gitlab",
            client_id=GITLAB_CLIENT_ID,
            client_secret=GITLAB_CLIENT_SECRET,
            server_metadata_url=f"{GITLAB_BASE_URL}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email read_user"},
        )
        logger.info("GitLab OAuth initialized successfully")
    else:
        logger.warning("GitLab OAuth not configured - some OAuth features may be unavailable")
except Exception as e:
    logger.error(f"Failed to initialize GitLab OAuth: {str(e)}")
    gitlab = None

# Add these constants
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))  # Default 60 minutes
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # Default 7 days

# Authentication Dependency
def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user

# Role-based authentication dependencies
def verify_user_role(user: dict, allowed_roles: List[UserRole]):
    if not user or user['role'] not in [role.value for role in allowed_roles]:
        raise HTTPException(
            status_code=403,
            detail=f"User must have one of these roles: {[role.value for role in allowed_roles]}"
        )
    return user

def require_roles(*roles: UserRole):
    def dependency(current_user: dict = Depends(get_current_user)):
        return verify_user_role(current_user, roles)
    return dependency

def student_only(current_user: dict = Depends(get_current_user)):
    return verify_user_role(current_user, [UserRole.STUDENT])

def tutor_only(current_user: dict = Depends(get_current_user)):
    return verify_user_role(current_user, [UserRole.TUTOR])

def admin_only(current_user: dict = Depends(get_current_user)):
    return verify_user_role(current_user, [UserRole.ADMIN])

def create_access_token(data: dict):
    """Create a new access token with configurable expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    """Create a new refresh token with longer expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "refresh": True})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/auth/refresh")
async def refresh_token(request: Request):
    """Endpoint to refresh an expired access token using refresh token"""
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")
            
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("refresh"):
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
        # Create new access token
        access_token = create_access_token({"sub": payload["sub"]})
        return {"access_token": access_token}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request):
    """Login endpoint with secure session handling"""
    try:
        redirect_uri = os.getenv("GITLAB_REDIRECT_URI")
        if not redirect_uri:
            raise ValueError("GITLAB_REDIRECT_URI environment variable not set")
            
        response = await gitlab.authorize_redirect(request, redirect_uri)
        
        # Set secure cookie options
        response.set_cookie(
            key="session_id",
            value=request.session.get("session_id"),
            httponly=True,
            secure=os.getenv("HTTPS_ENABLED", "True").lower() == "true",
            samesite="lax",
            max_age=TOKEN_EXPIRE_MINUTES * 60
        )
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get('/auth/callback')
async def auth_callback(request: Request):
    try:
        # Retrieve the access token from GitLab
        token = await gitlab.authorize_access_token(request)
        # Fetch user information
        user_data = token.get('userinfo')
    except Exception as e:
        raise HTTPException(status_code=400, detail="Authorization failed")

    # Save user information in session
    request.session['user'] = {
        'id': user_data['sub'],
        'name': user_data['name'],
        'email': user_data['email']
    }

    # Determine role of user
    group_pre = 'lsit-tutoring-platform/'
    group_names = [group_pre + stub for stub in ['admins', 'students', 'tutors']]
    role_names = ['admin', 'student', 'tutor']
    for i, group in enumerate(group_names):
        if group in user_data['groups_direct']:
            request.session['user']['role'] = role_names[i] # Set role
            break

    # If the user is an admin redirect to the verify admin page
    if request.session['user']['role'] == 'admin':
        return RedirectResponse(url='/admins/verify')
    # Otherwise if the user is a student or tutor redirect to the verify user page
    else:
        return RedirectResponse(url='/users/verify')

@router.get("/auth/logout")
async def logout(request: Request):
    # Clear the session
    request.session.clear()
    return RedirectResponse(url='/')