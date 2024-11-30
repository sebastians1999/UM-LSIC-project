from fastapi import APIRouter, Depends, HTTPException, Request  # Add Request import
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from routers.authentication import admin_only, limiter
from database.database import get_db, User, Chat, Message, Appointment
from utilities import get_user_by_id, get_chat_with_messages
from schemas.admin_schema import AdminDashboardResponse
from schemas.chat_schema import ChatResponse, MessageDeletedReponse, MessageSentResponse, MessageResponse, BanUserReponse
from schemas.user_schema import UserCreate, UserResponse
import logging

router = APIRouter('admin')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ADMINS = 7  # Add this constant at the top after imports

@router.get('/dashboard', response_model=AdminDashboardResponse)
@limiter.limit("10/minute")
async def admin_dashboard(db: Session = Depends(get_db), _=Depends(admin_only)):
    # Fetch admin dashboard data
    user_count = db.query(User).count()
    chat_count = db.query(Chat).count()
    appointment_count = db.query(Appointment).count()
    return {
        "user_count": user_count,
        "chat_count": chat_count,
        "appointment_count": appointment_count
    }

@router.get('/chats/{chatID}/messages', response_model=ChatResponse)
def get_chat_messages(chatID: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    return get_chat_with_messages(db, chatID)

@router.delete('/chats/delete/{messageID}', response_model=MessageDeletedReponse)
def delete_chat_message(messageID: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    # Delete a specific message in a chat
    message = db.query(Message).filter(Message.id == messageID).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_deleted = True
    db.commit()
    return {"message_id" : messageID, "message": f"Message {messageID} deleted"}

@router.post('/chats/{chatID}/messages', response_model=MessageSentResponse)
def send_chat_message(chatID: int, content: str, db: Session = Depends(get_db)):
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
def get_reports(db: Session = Depends(get_db)):
    # Retrieve all reports
    reports = db.query(Message).filter(Message.is_deleted == True).all()
    return {"reports": reports}

@router.get('/reports/{reportID}', response_model=MessageResponse)
@limiter.limit("10/minute")  # Add rate limiting
def get_report(reportID: int, db: Session = Depends(get_db)):
    # Retrieve detailed information about a specific report
    report = db.query(Message).filter(Message.id == reportID, Message.is_deleted == True).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}
    
@router.get('/users', response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db), _=Depends(admin_only)):
    # Retrieve all users
    users = db.query(User).all()
    return users

@router.get('/{id}', response_model=UserResponse)
@limiter.limit("10/minute")
def get_user(id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    return get_user_by_id(db, id)

@router.post('/users/{userID}/ban', response_model=BanUserReponse)
def ban_user(userID: int, ban_until: datetime, db: Session = Depends(get_db), admin=Depends(admin_only)):
    user = get_user_by_id(db, userID)
    user.is_banned_until = ban_until
    db.commit()
    return {"user_id": userID, "banned_until": ban_until, "issued_by": admin.id, "message": f"User {userID} banned until {ban_until}"}

@router.delete('/users/{userID}/delete')
@limiter.limit("3/minute")
def delete_user(
    userID: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_only)
):
    """Delete user with admin authentication and logging"""
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
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
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
