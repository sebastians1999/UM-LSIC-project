"""
Authentication router handling OAuth2 login flow with GitLab, user signup, token refresh and logout.
Implements JWT token based authentication with access and refresh tokens.
"""
from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter, Header
from fastapi.security import OAuth2AuthorizationCodeBearer, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from typing import List
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from typing import Union, Optional, Tuple
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError, jwt
from datetime import datetime, timedelta
from database.database import *
from logger import logger  # Add this import
from schemas.authentication_schema import LoggedInResponse, SignUpResponse, DecodedAccessToken, LoggedOutResponse, DecodedRefreshToken
from auth_tools import get_current_user, get_refresh_token
from database.redis import redis_client
from config import get_settings
import uuid
import os
import requests

# Check if we should use Redis
USE_REDIS = get_settings().use_redis

# Add OAuth2 scheme configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize app
router = APIRouter(prefix='/auth')

# Add rate limiting
limiter = Limiter(key_func=get_remote_address)

# Add OAuth configuration constants
GITLAB_CLIENT_ID = get_settings().gitlab_client_id
GITLAB_CLIENT_SECRET = get_settings().gitlab_client_secret
GITLAB_REDIRECT_URI = get_settings().gitlab_redirect_uri
GITLAB_BASE_URL = get_settings().gitlab_base_url
GITLAB_API_URL = get_settings().gitlab_api_url

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
SECRET_KEY = get_settings().secret_key
ALGORITHM = get_settings().hash_algorithm
TOKEN_EXPIRE_MINUTES = get_settings().access_token_expire_minutes 
REFRESH_TOKEN_EXPIRE_DAYS = get_settings().refresh_token_expire_days

# Token store
# This is a simple in-memory store for demonstration purposes, we should replace this with a database
# like Redis
refresh_token_store = {}

def verify_localhost(request: Request):
    """Verify that the request is coming from localhost"""
    host = request.client.host
    if host not in ["127.0.0.1", "localhost", "::1", "testclient"]:
        raise HTTPException(status_code=403, detail="Forbidden. This endpoint can only be accessed from localhost.")

def create_user_in_db(db: Session, user_data: dict, is_temp_admin: bool = False, replace: bool = False) -> User:
    """Create a new user in the database using the provided data.
    If is_temp_admin is True, the user will be created as a temporary admin account,
    which has the name "Admin" and email "admin@example.com".
    """
    if is_temp_admin:
        user_data = {
            "name": get_settings().admin_name,
            "email": get_settings().admin_email,
            "role": UserRole.ADMIN.name
        }
    else:
        assert 'name' in user_data, "Name is required to create a user"
        assert 'email' in user_data, "Email is required to create a user"
        assert 'role' in user_data, "Role is required to create a user"
        assert 'name' != "Admin", "Name cannot be 'Admin', as it is reserved for temporary admin accounts"
        assert 'email' != 'admin@example.com', "Email cannot be 'admin@example.com', as it is reserved for temporary admin accounts"

    # Check if the user already exists
    user = db.query(User).filter(User.email == user_data['email']).first()
    if user:
        if not replace:
            return user # Return the existing user
        
        # Remove the existing user
        db.delete(user)
        db.commit()

    user = User(
        name=user_data['name'],
        email=user_data['email'],
        role=user_data['role']
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def role_from_gitlab_group(user_groups: list) -> UserRole:
    group_pre = 'lsit-tutoring-platform/'
    role_mapping = {
        group_pre + 'admins': UserRole.ADMIN,
        group_pre + 'students': UserRole.STUDENT,
        group_pre + 'tutors': UserRole.TUTOR
    }
    
    for group, role in role_mapping.items():
        if group in user_groups:
            return role
            
    # Default to STUDENT if no matching role found
    return UserRole.STUDENT

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

def create_access_token(user_id: int, name: str, email: str, role: str, refresh_token_id: str, expires_in=TOKEN_EXPIRE_MINUTES):
    """Create a new access token with configurable expiration"""
    to_encode = {
        "sub": str(user_id), # Changed id to sub to adhere to JWT standard
        "name": name,
        "email": email,
        "role": role,
        "logged_in": True,
        "exp": datetime.utcnow() + timedelta(minutes=expires_in),
        "refresh_token_id": refresh_token_id
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> Tuple[str, str]:  # Changed from int to str
    """Create a refresh token. Returns the token and the token id"""
    token_id = str(uuid.uuid4())
    to_encode = {
        "sub": user_id,  # No need to convert to str since it's already a string UUID
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh": True,
        "token_id": token_id
    }
    # Store the refresh token
    refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Store the refresh token
    if USE_REDIS:
        redis_client.set_refresh_token(refresh_token, token_id, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60) # Expiration in seconds
    else:
        refresh_token_store[token_id] = refresh_token

    return refresh_token, token_id

def create_signup_token(user_id: str, name: str, email: str, role: str, expires_in=5):  # Changed from int
    """Create a JWT token for new users to sign up"""
    to_encode = {
        "sub": user_id,  # Already a string, no conversion needed
        "name": name,
        "email": email,
        "role": role.value if isinstance(role, UserRole) else role,
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
async def refresh_token(request: Request, db = Depends(get_db), payload : DecodedRefreshToken = Depends(get_refresh_token)):
    """Endpoint to refresh an expired access token using refresh token"""
    try:
        if not payload:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        # Check if payload.refresh is not set
        if "refresh_token_id" not in payload or not payload.refresh_token_id:
            if payload.role.name == "ADMIN":
                raise HTTPException(status_code=401, detail="Cannot refresh this token. Refresh token ID missing. This might be because you are using a temporary admin access token.")
            else:
                raise HTTPException(status_code=401, detail="Cannot refresh this token. Refresh token ID missing.")

        # Validate the refresh token by checking the memory store
        if USE_REDIS:
            user_id = redis_client.get_refresh_token(payload.token_id)
        else:
            user_id = refresh_token_store.get(payload.token_id, None)

        # If the refresh token is not found, then it is invalid
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token. The refresh token may have expired.")

        # Get user data from the database
        user = db.query(User).filter(User.id == payload.sub).first()
            
        # Create new access token
        access_token = create_access_token(user_id=payload.sub,
                                           name=user.name,
                                           email=user.email,
                                           role=user.role.name,
                                           refresh_token_id=payload.token_id)

        return {"access_token": access_token, "refresh_token": jwt.encode(payload.model_dump(), key=SECRET_KEY, algorithm=ALGORITHM), "token_type": "bearer", "status": "logged_in"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/login", response_model=Union[LoggedInResponse, SignUpResponse, None])
@limiter.limit("10/minute")
async def login(request: Request, gitlab_token = Depends(get_gitlab_token), db = Depends(get_db)):
    """Login endpoint"""
    # Fetch user info using the token with the gitlab object
    if (gitlab_token):
        user_info = get_gitlab_user_data(gitlab_token)

        role = role_from_gitlab_group(user_info['groups'])
        print(role)

        # Check if the user exists
        user = db.query(User).filter(User.email == user_info['email']).first()


        if user:
            logger.info(f"Logging in user {user.name}.")

            # Create a refresh token
            refresh_token, refresh_token_id = create_refresh_token(user.id)

            # Create an access token
            access_token = create_access_token(user.id, user.name, user.email, user.role.name, refresh_token_id)

            logger.info(f"Success. User {user.name} logged in.")

            return {"access_token": access_token, "refresh_token" : refresh_token, "token_type": "bearer", "status": "logged_in"}

        logger.info(f"User {user_info['name']} not found in the database.")

        # If the user does not exist, provide the client with a one time token to create an account
        token = create_signup_token(user_info['sub'], user_info['name'], user_info['email'], role)
    
        return {"message": "New user, sign up required", "status": "signup_required", "redirect_to": "/auth/signup?token=" + token}

    try:
        redirect_uri = GITLAB_REDIRECT_URI
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
        # Create a refresh token
        refresh_token, refresh_token_id = create_refresh_token(user.id)

        # Create an access token
        access_token = create_access_token(user.id, user.name, user.email, user.role.name, refresh_token_id)

        return {"access_token": access_token, "refresh_token" : refresh_token, "token_type": "bearer", "status": "logged_in"}

    # If the user does not exist, provide the client with a one time token to create an account
    token = create_signup_token(user_data['sub'], user_data['name'], user_data['email'], role)

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

        # Create the user
        user = create_user_in_db(db, payload)

        # Generate a refresh token
        refresh_token, refresh_token_id = create_refresh_token(user.id)

        # Generate an access token
        access_token = create_access_token(user.id, user.name, user.email, user.role.name, refresh_token_id)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "status": "logged_in"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/secure")
def secure_data(user: DecodedAccessToken = Depends(get_current_user)):
    """Secure endpoint that requires a valid token"""
    return {"message": "You have accessed secure data!", "user": user.model_dump()}

@router.get("/logout", response_model=LoggedOutResponse)
async def logout(request: Request, user: DecodedAccessToken = Depends(get_current_user)):
    # Invalidate the refresh token
    if USE_REDIS:
        redis_client.delete_refresh_token(user.refresh_token_id)
    else:
        del refresh_token_store[user.refresh_token_id]
    
    return {"message": "Logged out successfully. Refresh token invalidated.", "status": "logged_out"}

@router.get("/generate-admin-token")
def generate_admin_token(request: Request, response_model=LoggedInResponse, db : Session = Depends(get_db), _ = Depends(verify_localhost)):
    """
    Generate a temporary admin token for development purposes.
    Creates an admin user if it does not exist.
    Returns an access token associated with the admin user.
    This endpoint is only available in development, and can only be accessed from localhost.
    """

    # Only allow this endpoint in development
    if not get_settings().local:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Create a temporary admin account if it does not exist
    user = create_user_in_db(db, {}, is_temp_admin=True, replace=True)

    # Generate an access token
    access_token = create_access_token(user.id, user.name, user.email, user.role.name, "") # No refresh token for this type of token

    return {"access_token": access_token, "refresh_token": "", "token_type": "bearer", "status": "logged_in"}

