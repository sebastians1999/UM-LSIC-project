from sqlalchemy.orm import Session, joinedload
from database import User, Chat, Message, UserRole
from fastapi import HTTPException
from typing import Optional
from logger import logger

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID with error handling"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving user data")

def get_chat_with_messages(db: Session, chat_id: int) -> Optional[Chat]:
    """Get chat with all related data loaded"""
    try:
        chat = db.query(Chat).options(
            joinedload(Chat.student),
            joinedload(Chat.tutor),
            joinedload(Chat.messages).joinedload(Message.sender)
        ).filter(Chat.id == chat_id).first()

        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
            
        if not chat.student or not chat.tutor:
            logger.error(f"Chat {chat_id} has invalid student or tutor reference")
            raise HTTPException(status_code=404, detail="Chat data is incomplete")
            
        return chat
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving chat data")

def get_user_chats(db: Session, user_id: int, role: UserRole) -> list:
    """Get all chats for a user based on their role"""
    try:
        if role == UserRole.STUDENT:
            return db.query(Chat).filter(Chat.student_id == user_id).all()
        elif role == UserRole.TUTOR:
            return db.query(Chat).filter(Chat.tutor_id == user_id).all()
        return []
    except Exception as e:
        logger.error(f"Error retrieving chats for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving chat data")