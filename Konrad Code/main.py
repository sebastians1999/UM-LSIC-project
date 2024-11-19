from fastapi import FastAPI, Request
from fastapi.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from logger import logger
from admin import router as admin_router
from student import router as student_router
from tutor import router as tutor_router
from shared import router as shared_router
from mock_data import mock_users, mock_chats, mock_messages, mock_appointments, mock_reports

class LoggingMiddleware(BaseHTTPMiddleware):
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

app = FastAPI()

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(admin_router, prefix='/admin', tags=['admin'])
app.include_router(student_router, prefix='/student', tags=['student'])
app.include_router(tutor_router, prefix='/tutor', tags=['tutor'])
app.include_router(shared_router, tags=['shared'])  # Remove the prefix

@app.get("/mock/users")
def get_mock_users():
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
    logger.info("Server starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutting down...")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)