from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db, User, Chat, Message, UserRole, Appointment
from datetime import datetime
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import List, Optional
import logging

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserSimpleResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None  # Make email optional
    role: Optional[UserRole] = None  # Make role optional

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender: Optional[UserSimpleResponse] = None  # Make sender optional
    content: str
    timestamp: datetime
    is_deleted: bool

    class Config:
        orm_mode = True

class ChatResponse(BaseModel):
    id: int
    student: Optional[UserSimpleResponse] = None  # Make student optional
    tutor: Optional[UserSimpleResponse] = None  # Make tutor optional
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        orm_mode = True

@router.post('/initialize')
def initialize_admin(db: Session = Depends(get_db)):
    # Check if an admin already exists
    admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if admin_exists:
        return {"message": "Admin already initialized"}
    
    # Create admin user
    admin = User(
        email="admin@example.com",
        password=pwd_context.hash("hashed_password"),  # Replace with actual hashed password
        role=UserRole.ADMIN,
        name="Admin"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {"message": "Admin initialized"}

@router.post('/login')
def admin_login(email: str, password: str, db: Session = Depends(get_db)):
    # Authenticate admin
    admin = db.query(User).filter(User.email == email, User.role == UserRole.ADMIN).first()
    if not admin or not pwd_context.verify(password, admin.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Admin logged in"}

@router.get('/dashboard')
def admin_dashboard(db: Session = Depends(get_db)):
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
def get_chat_messages(chatID: int, db: Session = Depends(get_db)):
    try:
        # Ensure chat exists
        chat = db.query(Chat).filter(Chat.id == chatID).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Load relations with error handling
        chat = db.query(Chat).options(
            joinedload(Chat.student),
            joinedload(Chat.tutor),
            joinedload(Chat.messages).joinedload(Message.sender)
        ).filter(Chat.id == chatID).first()

        if not chat.student or not chat.tutor:
            logger.warning(f"Chat {chatID} has missing student or tutor reference")

        return chat
    except Exception as e:
        logger.error(f"Error retrieving messages for chat {chatID}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/chats/{chatID}/messages/{messageID}')
def delete_chat_message(chatID: int, messageID: int, db: Session = Depends(get_db)):
    # Delete a specific message in a chat
    message = db.query(Message).filter(Message.id == messageID, Message.chat_id == chatID).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_deleted = True
    db.commit()
    return {"message": f"Message {messageID} deleted from chat {chatID}"}

@router.post('/chats/{chatID}/messages')
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
    return {"message": f"Message sent to chat {chatID}"}

@router.get('/reports')
def get_reports(db: Session = Depends(get_db)):
    # Retrieve all reports
    reports = db.query(Message).filter(Message.is_deleted == True).all()
    return {"reports": reports}

@router.get('/reports/{reportID}')
def get_report(reportID: int, db: Session = Depends(get_db)):
    # Retrieve detailed information about a specific report
    report = db.query(Message).filter(Message.id == reportID, Message.is_deleted == True).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}

@router.post('/users/{userID}/ban')
def ban_user(userID: int, ban_until: datetime, db: Session = Depends(get_db)):
    db.commit()
    # Ban a specific user
    user = db.query(User).filter(User.id == userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned_until = ban_until
    db.commit()
    return {"message": f"User {userID} banned until {ban_until}"}
    return {"message": f"User {userID} banned until {ban_until}"}