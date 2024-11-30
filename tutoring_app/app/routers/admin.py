from fastapi import APIRouter, Depends, HTTPException, Request  # Add Request import
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from routers.authentication import admin_only, limiter
from database.database import get_db, User, Chat, Message, UserRole, Appointment, pwd_context
from utilities import get_user_by_id, get_chat_with_messages
from schemas.admin_schema import AdminDashboardResponse
from schemas.chat_schema import ChatResponse, MessageDeletedReponse, MessageSentResponse, MessageResponse, BanUserReponse
import logging

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ADMINS = 7  # Add this constant at the top after imports

@router.get('/dashboard', response_model=AdminDashboardResponse)
@limiter.limit("10/minute")
async def admin_dashboard(request: Request, db: Session = Depends(get_db), _=Depends(admin_only)):
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

@router.delete('/chats/{chatID}/messages/{messageID}', response_model=MessageDeletedReponse)
def delete_chat_message(chatID: int, messageID: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    # Delete a specific message in a chat
    message = db.query(Message).filter(Message.id == messageID, Message.chat_id == chatID).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_deleted = True
    db.commit()
    return {"chat_id" : chatID, "message_id" : messageID, "message": f"Message {messageID} deleted from chat {chatID}"}

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
def get_reports(request: Request, db: Session = Depends(get_db)):
    # Retrieve all reports
    reports = db.query(Message).filter(Message.is_deleted == True).all()
    return {"reports": reports}

@router.get('/reports/{reportID}', response_model=MessageResponse)
@limiter.limit("10/minute")  # Add rate limiting
def get_report(request: Request, reportID: int, db: Session = Depends(get_db)):
    # Retrieve detailed information about a specific report
    report = db.query(Message).filter(Message.id == reportID, Message.is_deleted == True).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}

@router.post('/users/{userID}/ban', response_model=BanUserReponse)
def ban_user(userID: int, ban_until: datetime, db: Session = Depends(get_db), admin=Depends(admin_only)):
    user = get_user_by_id(db, userID)
    user.is_banned_until = ban_until
    db.commit()
    return {"user_id": userID, "banned_until": ban_until, "issued_by": admin.id, "message": f"User {userID} banned until {ban_until}"}