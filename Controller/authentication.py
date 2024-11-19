from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse

from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

import httpx
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize app
router = APIRouter()

logger = logging.getLogger('uvicorn.error')

# Add session middleware with a secret key to sign the session cookie
router.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "a_random_secret_key"))

# GitLab OAuth2 environment variables
# When working locally, these variables should be set in a .env file
# You can find these values in the GitLab application settings (or ask me - Nate)
# Never hardcode these values in your code in case you accidentally commit them to GitHub
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET")
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI")
GITLAB_BASE_URL = os.getenv("GITLAB_BASE_URL")

# OAuth2 configuration
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
    server_metadata_url=config.get("GITLAB_SERVER_METADATA_URL"),
    client_kwargs={"scope": "openid profile email read_user"},
)

# Authentication Dependency
def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user

@router.get("/auth/login")
async def login(request: Request):
    # Redirect user to GitLab login page
    redirect_uri = GITLAB_REDIRECT_URI
    return await gitlab.authorize_redirect(request, redirect_uri)

@router.get('/auth/callback')
async def auth_callback(request: Request):
    try:
        # Retrieve the access token from GitLab
        token = await gitlab.authorize_access_token(request)
        logger.info(f"Access token: {token}")
        # Fetch user information
        user_data = token.get('userinfo')
        logger.info(f"User data: {user_data}")
    except Exception as e:
        logger.error(f"Failed to get user data: {e}")
        raise HTTPException(status_code=400, detail="Authorization failed")

    logger.info(f"User data: {user_data}")

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