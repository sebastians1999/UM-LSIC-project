from pydantic import BaseModel, field_validator, EmailStr
from database.database import UserRole
from bleach import clean

class AdminBase(BaseModel):
    """Base admin data"""
    email: EmailStr
    name: str
    role: UserRole = UserRole.ADMIN

    @field_validator('name')
    def sanitize_name(cls, v):
        return clean(v, strip=True)

class AdminDashboardResponse(BaseModel):
    """Admin dashboard data"""
    user_count: int
    chat_count: int
    appointment_count: int
