from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from auth_tools import get_current_user
from database.database import get_db, User, Message, UserRole
from config import get_settings
from utilities import get_user_by_id, get_user_chats, get_chat_with_messages
from schemas.chat_schema import ChatResponse, MessageResponse
from schemas.authentication_schema import DecodedAccessToken
from logger import logger
from database.redis import redis_client
import json
#hi
# Check if we should use Redis
USE_REDIS = get_settings().use_redis
router = APIRouter(prefix='/chats')

@router.get('/', response_model=List[ChatResponse])
def get_chats(request: Request, current_user=Depends(get_current_user), db: Session=Depends(get_db)):
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
    # Optionally, cache the result
    # redis_client.set_cache(cache_key, json.dumps(detailed_chats), expiration=600)

    return detailed_chats

@router.get('/{chatID}', response_model=ChatResponse)
def get_chat(request: Request, chatID: str, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):  # Changed from int to str
    chat = db.query(Chat).filter(Chat.id == chatID).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Verify user has access to this chat
    if chat.student_id != current_user.sub and chat.tutor_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return chat

@router.post('/{chatID}/messages', response_model=MessageResponse)
def send_message(
    request: Request,
    chatID: str,  # Changed from int
    content: str,
    current_user: DecodedAccessToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in an existing chat from the logged in user."""
    try:
        sender = User.get_by_id(db, current_user.sub)  # Use get_by_id method
        
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
        
        # Invalidate cache after sending a message
        redis_client.delete_cache(f"chat_{chatID}")
        redis_client.delete_cache(f"chats_{current_user.sub}")
        # Optionally, delete cache for the other user involved in the chat
        
        return message
    except Exception as e:
        logger.error(f"Error sending message in chat {chatID}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while sending message")
