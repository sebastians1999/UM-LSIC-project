from pydantic import BaseModel
from user_schema import UserResponse
from datetime import datetime
from typing import List

class ReportBase(BaseModel):
    """Report request data"""
    reason: str
    created_at: datetime
    by: int # Reporter ID

class ReportMessage(ReportBase):
    """Report message request data"""
    message_id: int

class ReportUser(ReportBase):
    """Report user request data"""
    user_id: int

class ReportMessageResponse(ReportMessage):
    """Report message response data"""
    id: int
    message: str

class ReportUserResponse(ReportUser):
    """Report user response data"""
    id: int
    user: str