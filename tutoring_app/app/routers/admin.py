"""
Admin router providing administrative endpoints for managing users, chats, reports and dashboard.
Requires admin authentication for all endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request  # Add Request import
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from routers.authentication import limiter
from auth_tools import admin_only
from database.database import get_db, User, Chat, Message, Appointment
from utilities import get_user_by_id, get_chat_with_messages
from schemas.admin_schema import AdminDashboardResponse
from schemas.chat_schema import ChatResponse, MessageDeletedReponse, MessageSentResponse, MessageResponse, BanUserReponse
from schemas.user_schema import UserCreate, UserResponse
import logging
from database.redis import redis_client
import json
from config import get_settings  # Add the missing import for get_settings

#hi
router = APIRouter(prefix='/admin')
USE_REDIS = get_settings().use_redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ADMINS = 7  # Add this constant at the top after imports

@router.get('/dashboard', response_model=AdminDashboardResponse)
@limiter.limit("10/minute")
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    """
    Fetch admin dashboard data including user count, chat count and appointment count.
    Rate limited to 10 requests per minute.
    
    Returns:
        AdminDashboardResponse: Dashboard statistics
    """
    if USE_REDIS:
        cache_key = "admin_dashboard_data"
        cached_data = redis_client.get_cache(cache_key)
        if cached_data:
            print('Returning cached data')
            return json.loads(cached_data)

    # Fetch admin dashboard data
    user_count = db.query(User).count()
    chat_count = db.query(Chat).count()
    appointment_count = db.query(Appointment).count()

    data = {
        "user_count": user_count,
        "chat_count": chat_count,
        "appointment_count": appointment_count
    }
    if USE_REDIS:
        redis_client.set_cache(cache_key, json.dumps(data, default=str), expiration=600)  # Cache for 10 minutes
    
    return data

@router.get('/chats/{chatID}/messages', response_model=ChatResponse)
def get_chat_messages(request: Request, chatID: str, db: Session = Depends(get_db), _=Depends(admin_only)):  
    """
    Fetches messages for a specific chat.

    Args:
        request (Request): The request object.
        chatID (str): The ID of the chat to fetch messages for.
        db (Session): The database session dependency.
        _ (Depends): Dependency to ensure the user is an admin.

    Returns:
        ChatResponse: The response model containing chat messages.
    """
    return get_chat_with_messages(db, chatID)

@router.delete('/chats/delete/{messageID}', response_model=MessageDeletedReponse)
def delete_chat_message(request: Request, messageID: str, db: Session = Depends(get_db), _=Depends(admin_only)):  # Changed from int
    """
    Delete a specific message in a chat.

    Args:
        request (Request): The request object.
        messageID (str): The ID of the message to be deleted.
        db (Session, optional): The database session. Defaults to Depends(get_db).
        _ (Depends, optional): Dependency to ensure the user is an admin. Defaults to Depends(admin_only).

    Raises:
        HTTPException: If the message with the given ID is not found.

    Returns:
        dict: A dictionary containing the message ID and a confirmation message.
    """
    # Delete a specific message in a chat
    message = db.query(Message).filter(Message.id == messageID).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_deleted = True
    db.commit()
    return {"message_id" : messageID, "message": f"Message {messageID} deleted"}

@router.post('/chats/{chatID}/messages', response_model=MessageSentResponse)
def send_chat_message(request: Request, chatID: str, content: str, db: Session = Depends(get_db), _=Depends(admin_only)):  # Changed from int
    """
    Sends a message to a specific chat.

    Args:
        request (Request): The request object.
        chatID (str): The ID of the chat to which the message will be sent.
        content (str): The content of the message to be sent.
        db (Session, optional): The database session dependency. Defaults to Depends(get_db).
        _ (Depends, optional): The admin-only dependency. Defaults to Depends(admin_only).

    Returns:
        dict: A dictionary containing the message ID, chat ID, and a confirmation message.
    """
    # Send a message to a specific chat
    message = Message(
        chat_id=chatID,
        sender_id=1,  # Assuming admin ID is 1
        content=content,
        timestamp=datetime.now()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"message_id": message.id, "chat_id": chatID, "message": f"Message sent to chat {chatID}"}

@router.get('/reports')
@limiter.limit("10/minute")  # Add rate limiting
def get_reports(request: Request, db: Session = Depends(get_db), _=Depends(admin_only)):
    """
    Retrieve all deleted reports from the database.

    Args:
        request (Request): The HTTP request object.
        db (Session, optional): The database session dependency. Defaults to Depends(get_db).
        _ (Depends, optional): Dependency to ensure the user has admin privileges. Defaults to Depends(admin_only).

    Returns:
        dict: A dictionary containing a list of deleted reports.
    """
    # Retrieve all reports
    reports = db.query(Message).filter(Message.is_deleted == True).all()
    return {"reports": reports}

@router.get('/reports/{reportID}', response_model=MessageResponse)
@limiter.limit("10/minute")  # Add rate limiting
def get_report(request: Request, reportID: str, db: Session = Depends(get_db), _=Depends(admin_only)):  # Changed from int to str
    """
    Retrieve detailed information about a specific report.

    Args:
        request (Request): The request object.
        reportID (str): The ID of the report to retrieve.
        db (Session, optional): The database session dependency. Defaults to Depends(get_db).
        _ (Depends, optional): The admin-only dependency. Defaults to Depends(admin_only).

    Raises:
        HTTPException: If the report is not found, raises a 404 HTTP exception.

    Returns:
        dict: A dictionary containing the report details.
    """
    # Retrieve detailed information about a specific report
    report = db.query(Message).filter(Message.id == reportID, Message.is_deleted == True).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}
    
@router.get('/users', response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db), _=Depends(admin_only)):
    """
    Retrieve all users from the database.

    Args:
        db (Session): Database session dependency.
        _ (Depends): Dependency to ensure the user has admin privileges.

    Returns:
        List[User]: A list of all users in the database.
    """
    # Retrieve all users
    users = db.query(User).all()
    return users

@router.get('/{id}', response_model=UserResponse)
@limiter.limit("10/minute")
def get_user(request: Request, id: str, db: Session = Depends(get_db), _=Depends(admin_only)):  # Changed from int
    """
    Retrieve a user by their ID.

    Args:
        request (Request): The request object.
        id (str): The ID of the user to retrieve.
        db (Session, optional): The database session. Defaults to Depends(get_db).
        _ (Depends, optional): Dependency to ensure the user has admin privileges. Defaults to Depends(admin_only).

    Returns:
        User: The user object retrieved from the database.
    """
    return get_user_by_id(db, id) 

@router.post('/users/{userID}/ban', response_model=BanUserReponse)
def ban_user(request: Request, userID: str, ban_until: datetime, db: Session = Depends(get_db), admin=Depends(admin_only)):  # Changed from int to str
    """
    Ban a user until a specified datetime.

    Args:
        request (Request): The request object.
        userID (str): The ID of the user to be banned.
        ban_until (datetime): The datetime until which the user is banned.
        db (Session, optional): The database session. Defaults to Depends(get_db).
        admin (Admin, optional): The admin issuing the ban. Defaults to Depends(admin_only).

    Returns:
        dict: A dictionary containing the user ID, ban expiration datetime, admin ID, and a message.
    """
    user = get_user_by_id(db, userID)
    user.is_banned_until = ban_until
    db.commit()
    return {"user_id": userID, "banned_until": ban_until, "issued_by": admin.id, "message": f"User {userID} banned until {ban_until}"}

@router.delete('/users/{userID}/delete')
@limiter.limit("3/minute")
def delete_user(
    request: Request,
    userID: str,  # Changed from int to str
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_only)
):

    """
    Delete user with admin authentication and logging.

    Args:
        request (Request): The request object.
        userID (str): The ID of the user to delete.
        db (Session): The database session dependency.
        current_user (dict): The current authenticated admin user.

    Returns:
        dict: A message indicating the user has been deleted.

    Raises:
        HTTPException: If the user is not found or an error occurs during deletion.
    """
    try:
        user = db.query(User).filter(User.id == userID).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"User {userID} deleted by admin {current_user['id']}")
        db.delete(user)
        db.commit()
        return {"message": f"User {userID} deleted"}
    except Exception as e:
        logger.error(f"Error deleting user {userID}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting user")

@router.post('/users/create')
@limiter.limit("3/minute")
def create_user(request: Request, user_data: UserCreate, db: Session = Depends(get_db), _=Depends(admin_only)):
    """
    Create a new user. Only admins can create users this way, normally it requires GitLab authentication.
    Args:
        request (Request): The request object.
        user_data (UserCreate): The data required to create a new user.
        db (Session, optional): The database session. Defaults to Depends(get_db).
        _ (Depends, optional): Dependency to ensure only admins can access this function. Defaults to Depends(admin_only).
    Raises:
        HTTPException: If the email is already registered.
        HTTPException: If there is an error creating the user.
    Returns:
        dict: A dictionary containing a success message and the user ID of the newly created user.
    """
    """Create a new user. Only admins can create users this way, normmally it requires gitlab authentication."""

    # Check if user already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,  # Add role from request
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created: {user.email}")
        return {"message": "User created successfully", "user_id": user.id}
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating user")
    
@router.delete('/reports/{reportID}', response_model=MessageResponse)
@limiter.limit("10/minute")  # Add rate limiting
def delete_report(request: Request, reportID: str, db: Session = Depends(get_db), _=Depends(admin_only)):
    """
    Delete a specific report by ID.

    Args:
        request (Request): The request object.
        reportID (str): The ID of the report to delete.
        db (Session, optional): The database session dependency. Defaults to Depends(get_db).
        _ (Depends, optional): The admin-only dependency. Defaults to Depends(admin_only).

    Raises:
        HTTPException: If the report is not found or an error occurs during deletion.

    Returns:
        dict: A dictionary containing a success message.
    """
    try:
        report = db.query(Message).filter(Message.id == reportID).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        db.delete(report)
        db.commit()
        return {"message": f"Report {reportID} deleted"}
    except Exception as e:
        logger.error(f"Error deleting report {reportID}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting report")