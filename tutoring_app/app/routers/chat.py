from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from auth_tools import get_current_user
from database.database import get_db, User, Message, UserRole
from utilities import get_user_by_id, get_user_chats, get_chat_with_messages
from schemas.chat_schema import ChatResponse, MessageResponse
from schemas.authentication_schema import DecodedAccessToken
from logger import logger

router = APIRouter('chats')

@router.get('/', response_model=List[ChatResponse])
def get_chats(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_id(db, current_user.sub)
    chats = get_user_chats(db, user.id, user.role)
    detailed_chats = []
    for chat in chats:
        detailed_chats.append({
            "id": chat.id,
            "student": {
                "id": chat.student.id,
                "email": chat.student.email,
                "role": chat.student.role,
                "name": chat.student.name,
                "created_at": None
            },
            "tutor": {
                "id": chat.tutor.id,
                "email": chat.tutor.email,
                "role": chat.tutor.role,
                "name": chat.tutor.name,
                "created_at": None
            },
            "created_at": chat.created_at,
            "updated_at": chat.updated_at
        })
    return detailed_chats

@router.get('/{chatID}', response_model=ChatResponse)
def get_chat(chatID: int, current_user : DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_chat_with_messages(db, chatID)
    # Check that the user is part of the chat
    if (current_user.role != UserRole.ADMIN.value) and (chat.student_id != current_user.sub and chat.tutor_id != current_user.sub):
        raise HTTPException(status_code=403, detail="User not authorized to view chat")

    return get_chat_with_messages(db, chatID)

@router.post('/{chatID}/messages', response_model=MessageResponse)
def send_message(chatID: int, content: str, current_user : DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    """Send a message in an existing chat from the logged in user."""
    try:
        # Ensure the sender exists
        sender = db.query(User).filter(User.id == current_user.sub).first()
            
        # Send a message in an existing chat
        message = Message(
            chat_id=chatID,
            sender_id=sender.id,
            content=content,
            timestamp=datetime.now()
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    except Exception as e:
        logger.error(f"Error sending message in chat {chatID}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while sending message")