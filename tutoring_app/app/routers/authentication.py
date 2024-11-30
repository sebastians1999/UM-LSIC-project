from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter, Header
from fastapi.security import OAuth2AuthorizationCodeBearer, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from typing import List
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from typing import Union, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError, jwt
from datetime import datetime, timedelta
from database.database import *
from logger import logger  # Add this import
from schemas.authentication_schema import LoggedInResponse, SignUpResponse, DecodedAccessToken
from auth_tools import get_current_user
import httpx
import os
import requests

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = [
    'SECRET_KEY',
    'TOKEN_EXPIRE_MINUTES',
    'REFRESH_TOKEN_EXPIRE_DAYS',
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
router = APIRouter(prefix='/auth')

# Add rate limiting
limiter = Limiter(key_func=get_remote_address)

# Add OAuth configuration constants
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET")
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI")
GITLAB_BASE_URL = os.getenv("GITLAB_BASE_URL", "https://gitlab.com")
GITLAB_API_URL = os.getenv("GITLAB_API_URL", f"{GITLAB_BASE_URL}/oauth/userinfo")

# Initialize OAuth only if credentials are available
oauth = None
gitlab = None

try:
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
except Exception as e:
    logger.error(f"Failed to initialize GitLab OAuth: {str(e)}")
    raise e

# Add these constants
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))  # Default 60 minutes
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # Default 7 days

# Token store
# This is a simple in-memory store for demonstration purposes, we should replace this with a database
# like Redis
refresh_token_store = {}

def role_from_gitlab_group(user_groups : list):
    # Determine role of user
    group_pre = 'lsit-tutoring-platform/'
    group_names = [group_pre + group_stub for group_stub in ['admins', 'students', 'tutors']]
    role_names = ['ADMIN', 'STUDENT', 'TUTOR']
    role = ""
    for i, group in enumerate(group_names):
        if group in user_groups:
            role = role_names[i]
            break

    return role

# Optional gitlab token dependency
def get_gitlab_token(authorization: Optional[str] = Header(None)):
    if authorization:
        # Extract token from the Authorization header
        token = authorization.split("Bearer ")[-1]
        return token
    return None  # Return None if no token is provided

# Function to fetch GitLab user data using the access token
def get_gitlab_user_data(access_token: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(f'{GITLAB_API_URL}', headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="GitLab authentication failed")

    return response.json()

def create_access_token(user_id: int, name: str, email: str, role: str, expires_in=TOKEN_EXPIRE_MINUTES):
    """Create a new access token with configurable expiration"""
    to_encode = {
        "sub": user_id, # Changed id to sub to adhere to JWT standard
        "name": name,
        "email": email,
        "role": role,
        "logged_in": True,
        "exp": datetime.utcnow() + timedelta(minutes=expires_in)

    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id : int):
    """Create a new refresh token with longer expiration"""
    to_encode = {"sub": user_id, "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh": True}
    # Store the refresh token
    refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token_store[refresh_token] = {"user_id": user_id, "expires_at": to_encode["exp"]}
    return refresh_token

def create_signup_token(user_id: int, name: str, email: str, role: str, expires_in=5):
    """Create a JWT token for new users to sign up"""
    to_encode = {
        "sub": user_id,
        "name": name,
        "email": email,
        "role": role,
        "logged_in": False,
        "exp": datetime.utcnow() + timedelta(minutes=expires_in)
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)):
    """Token verification logic"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload # Return the decoded token 
    except JWTError: # Invalid or expired token
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/refresh", response_model=LoggedInResponse)
async def refresh_token(request: Request, db = Depends(get_db)):
    """Endpoint to refresh an expired access token using refresh token"""
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")
            
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("refresh"):
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Get user data from the database
        user = db.query(User).filter(User.id == payload["sub"]).first()
            
        # Create new access token
        access_token = create_access_token(user_id=payload["sub"],
                                           name=user.name,
                                           email=user.email,
                                           role=user.role.name)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/login", response_model=Union[LoggedInResponse, None])
@limiter.limit("10/minute")
async def login(request: Request, gitlab_token = Depends(get_gitlab_token), db = Depends(get_db)):
    """Login endpoint"""
    # Fetch user info using the token with the gitlab object
    if gitlab_token:
        user_info = get_gitlab_user_data(gitlab_token)

        role = role_from_gitlab_group(user_info['groups'])

        # Check if the user exists
        user = db.query(User).filter(User.email == user_info['email']).first()


        if user:
            logger.info(f"Logging in user {user.name}.")

            # Create an access token
            access_token = create_access_token(user.id, user.name, user.email, user.role.name)

            # Create a refresh token
            refresh_token = create_refresh_token(user.id)

            logger.info(f"Success. User {user.name} logged in.")

            return {"access_token": access_token, "refresh_token" : refresh_token, "token_type": "bearer"}

        logger.info(f"User {user_info['name']} not found in the database.")

        # If the user does not exist, provide the client with a one time token to create an account
        token = create_signup_token(user_info['sub'], user_info['name'], user_info['email'], role)
    
        return {"message": "New user, sign up required", "status": "signup_required", "redirect_to": "/auth/signup?token=" + token}

    try:
        redirect_uri = os.getenv("GITLAB_REDIRECT_URI")
        if not redirect_uri:
            raise ValueError("GITLAB_REDIRECT_URI environment variable not set")
            
        response = await gitlab.authorize_redirect(request, redirect_uri)
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get('/callback', response_model=Union[LoggedInResponse, SignUpResponse])
async def auth_callback(request: Request, db = Depends(get_db)):
    """Callback endpoint after successful authentication with GitLab. Returns a JWT token which should be used by the client"""
    try:
        # Retrieve the access token from GitLab
        token = await gitlab.authorize_access_token(request)
        # Fetch user information
        user_data = token.get('userinfo')
    except Exception as e:
        raise HTTPException(status_code=400, detail="Authorization failed")

    # Determine role of user
    group_pre = 'lsit-tutoring-platform/'
    group_names = [group_pre + stub for stub in ['admins', 'students', 'tutors']]
    role_names = ['admin', 'student', 'tutor']
    role = ""
    for i, group in enumerate(group_names):
        if group in user_data['groups_direct']:
            role = role_names[i]
            break

    # Check if the user is already in the database, by email
    user = db.query(User).filter(User.email == user_data['email']).first()

    # If the user exists, log them in by giving them a new access token
    if user:
        # Create an access token
        access_token = create_access_token(user.id, user.name, user.email, user.role.name)

        # Create a refresh token
        refresh_token = create_refresh_token(user.id)

        return {"access_token": access_token, "refresh_token" : refresh_token, "token_type": "bearer"}

    # If the user does not exist, provide the client with a one time token to create an account
    token = create_access_token(user_data['sub'], user_data['name'], user_data['email'], role)

    return {'message': 'New user, sign up required.',
            'status': 'signup_required',
            'redirect_to': f'/auth/signup?token={token}'} # Include the token in the redirect URL

@router.post("/signup", response_model=LoggedInResponse)
@limiter.limit("10/minute")
def signup(request : Request, token: str, db = Depends(get_db)):
    """Sign up endpoint. Requires a one time JWT token which is generated after successful authentication - see auth_callback."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if the user already exists
        user = db.query(User).filter(User.email == payload['email']).first()

        if user:
            raise HTTPException(status_code=400, detail="User already exists")

        # Create a new user
        user = User(
            name=payload['name'],
            email=payload['email'],
            role=payload['role'],
            created_at = datetime.now(),
            updated_at = datetime.now()
        )

        # Add the user to the database
        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate an access token
        access_token = create_access_token(user.id, user.name, user.email, user.role.name)

        # Generate a refresh token
        refresh_token = create_refresh_token(user.id)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/secure")
def secure_data(user: DecodedAccessToken = Depends(get_current_user)):
    """Secure endpoint that requires a valid token"""
    return {"message": "You have accessed secure data!", "user": user.model_dump()}

@router.get("/logout")
async def logout(request: Request):
    # Invalidate the access token and refresh token
    return RedirectResponse(url='/')