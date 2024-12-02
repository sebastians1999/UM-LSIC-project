from pydantic import BaseModel
from schemas.user_schema import UserResponse
from datetime import datetime
from typing import List

class MessageResponse(BaseModel):
    """Message response data"""
    id: str  # Changed from int
    chat_id: str  # Changed from int
    sender: UserResponse
    content: str
    timestamp: datetime
    is_deleted: bool

    class Config:
        orm_mode = True

class ChatResponse(BaseModel):
    """Chat response data. A chat is a conversation between a student and tutor and is like a container for messages."""
    id: str  # Changed from int
    student: UserResponse
    tutor: UserResponse
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        orm_mode = True

class MessageDeletedReponse(BaseModel):
    """Chat deleted response data"""
    message_id: str  # Changed from int
    message: str

class MessageSentResponse(BaseModel):
    """Message sent response data"""
    message_id: str  # Changed from int
    chat_id: str  # Changed from int
    message: str

class BanUserReponse(BaseModel):
    """Ban user response data"""
    user_id: str  # Changed from int
    banned_until: datetime
    issued_by: str  # Changed from int
    message: str