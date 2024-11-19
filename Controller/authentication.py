from fastapi import FastAPI, Depends, HTTPException, Request
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
app = FastAPI()

logger = logging.getLogger('uvicorn.error')

# Add session middleware with a secret key to sign the session cookie
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "a_random_secret_key"))

# GitLab OAuth2 environment variables
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

@app.get('/')
async def home(request: Request):
    # Check if user is authenticated
    if 'user' in request.session:
        return {"message": "Hello World! You are logged in. Go to /secure-data to see secure data."}

    return {"message": "Hello World! Go to /login to login with GitLab."}

@app.get("/login")
async def login(request: Request):
    # Redirect user to GitLab login page
    redirect_uri = GITLAB_REDIRECT_URI
    return await gitlab.authorize_redirect(request, redirect_uri)

@app.get('/auth/callback')
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

    return user_data

@app.get("/logout")
async def logout(request: Request):
    # Clear the session
    request.session.clear()
    return RedirectResponse(url='/')

@app.get("/secure-data")
async def secure_data(user: dict = Depends(get_current_user)):
    return {"message": "This is secure data!", "user": user}