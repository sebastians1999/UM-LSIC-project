from fastapi import FastAPI, Request
from functools import lru_cache
from datetime import datetime
import os, sys
from dotenv import load_dotenv
from logger import logger
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from mock_data import mock_users, mock_chats, mock_messages, mock_appointments, mock_reports, mock_tutors
from config import get_settings

### ROUTERS
from routers.admin import router as admin_router
from routers.appointment import router as appointment_router
from routers.authentication import router as auth_router
from routers.chat import router as chat_router
from routers.report import router as report_router
from routers.support import router as support_router
from routers.user  import router as user_router


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

app = FastAPI(
    title=get_settings().app_name,
    version=get_settings().app_version,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# More secure session configuration with environment variables
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().secret_key,
    max_age=get_settings().session_expire_minutes * 60,  # Convert minutes to seconds
    same_site="lax",
    https_only=get_settings().https_enabled
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
app.include_router(admin_router, tags=['admin'])
app.include_router(appointment_router, tags=['appointments'])
app.include_router(auth_router, tags=['authentication'])
app.include_router(chat_router, tags=['chat'])
app.include_router(report_router, tags=['report'])
app.include_router(support_router, tags=['support'])
app.include_router(user_router, tags=['users'])

@app.get("/")
def read_root():
    """
    Root endpoint returning API welcome message.

    Returns:
    - dict: Welcome message
    """
    return {"message": "Welcome to the Tutoring API!!! This is a test!"}

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
    uvicorn.run(app, host=get_settings().app_host, port=get_settings().app_port)