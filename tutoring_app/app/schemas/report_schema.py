from pydantic import BaseModel
from schemas.user_schema import UserResponse
from datetime import datetime
from typing import List

class ReportBase(BaseModel):
    """Report request data"""
    reason: str
    created_at: datetime
    by: str  # Changed from int to str for UUID

class ReportMessage(ReportBase):
    """Report message request data"""
    message_id: str  # Changed from int to str for UUID

class ReportUser(ReportBase):
    """Report user request data"""
    user_id: str  # Changed from int to str for UUID

class ReportMessageResponse(ReportMessage):
    """Report message response data"""
    id: str  # Changed from int to str for UUID
    message: str

class ReportUserResponse(ReportUser):
    """Report user response data"""
    id: str  # Changed from int to str for UUID
    user: str