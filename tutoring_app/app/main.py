from fastapi import FastAPI, Request
from datetime import datetime
import os, sys
from dotenv import load_dotenv
from logger import logger
from routers.admin import router as admin_router
from routers.student import router as student_router
from tutor import router as tutor_router
from shared import router as shared_router
from authentication import router as auth_router
from mock_data import mock_users, mock_chats, mock_messages, mock_appointments, mock_reports, mock_tutors
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    
    Logs request method, URL, response status, and timing information.
    Handles errors by logging exceptions.
    """
    async def dispatch(self, request: Request, call_next):
        # Log request
        start_time = datetime.now()
        logger.info(f"Request: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            # Log response
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Response: {response.status_code} - Duration: {duration:.3f}s")
            return response
        except Exception as e:
            # Log error
            logger.error(f"Error processing request: {str(e)}")
            raise

def setup_gitlab_oauth():
    """Interactive setup for GitLab OAuth credentials"""
    print("\nGitLab OAuth Setup Required")
    print("---------------------------")
    print("1. Go to https://gitlab.com/-/profile/applications")
    print("2. Create a new application with these settings:")
    print("   - Name: Tutoring Platform")
    print("   - Redirect URI: http://localhost:8000/auth/callback")
    print("   - Scopes: read_user, openid, profile, email")
    print("3. Copy the provided Client ID and Client Secret")
    
    client_id = input("\nEnter your GitLab Client ID: ").strip()
    client_secret = input("Enter your GitLab Client Secret: ").strip()
    
    # Update .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_path, 'a') as f:
        f.write(f"\nGITLAB_CLIENT_ID={client_id}")
        f.write(f"\nGITLAB_CLIENT_SECRET={client_secret}")
        f.write("\nGITLAB_REDIRECT_URI=http://localhost:8000/auth/callback")
        f.write("\nGITLAB_BASE_URL=https://gitlab.com")
    
    print("\nCredentials saved to .env file")
    print("Restart the application to apply changes")
    sys.exit(0)

# Add this before app initialization
load_dotenv()
if not os.getenv("GITLAB_CLIENT_ID") or not os.getenv("GITLAB_CLIENT_SECRET"):
    setup_gitlab_oauth()

app = FastAPI()

# Load and validate environment variables
load_dotenv()

required_env_vars = [
    'SECRET_KEY',
    #'FRONTEND_URL',
    'SESSION_EXPIRE_MINUTES',
    'HTTPS_ENABLED'
]

# Validate required environment variables
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# More secure session configuration with environment variables
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    max_age=int(os.getenv("SESSION_EXPIRE_MINUTES", 60)) * 60,  # Convert minutes to seconds
    same_site="lax",
    https_only=os.getenv("HTTPS_ENABLED", "True").lower() == "true"
)

# Add CORS middleware with environment configuration
app.add_middleware(
    CORSMiddleware,
    #allow_origins=[os.environ.get("FRONTEND_URL")],
    allow_origins=['*'], # Allow all origins for now
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600
)

# Include routers
app.include_router(admin_router, prefix='/admin', tags=['admin'])
app.include_router(student_router, prefix='/student', tags=['student'])
app.include_router(tutor_router, prefix='/tutor', tags=['tutor'])
app.include_router(shared_router, tags=['shared'])  # Remove the prefix
app.include_router(auth_router, tags=['auth'])

@app.get("/")
def read_root():
    """
    Root endpoint returning API welcome message.

    Returns:
    - dict: Welcome message
    """
    return {"message": "Welcome to the Tutoring API!"}

@app.get("/mock/users")
def get_mock_users():
    """
    Get mock user data for testing.
    
    Returns:
    - dict: List of mock users
    """
    return {"users": mock_users}

@app.get("/mock/chats")
def get_mock_chats():
    return {"chats": mock_chats}

@app.get("/mock/messages")
def get_mock_messages():
    return {"messages": mock_messages}

@app.get("/mock/appointments")
def get_mock_appointments():
    return {"appointments": mock_appointments}

@app.get("/mock/reports")
def get_mock_reports():
    return {"reports": mock_reports}

@app.get("/mock/tutors")
def get_mock_tutors():
    return {"tutors": mock_tutors}

@app.on_event("startup")
async def startup_event():
    """
    Application startup handler.
    Initializes services and logs startup.
    """
    logger.info("Server starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutting down...")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)