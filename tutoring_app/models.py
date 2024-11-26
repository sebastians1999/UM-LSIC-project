from pydantic import BaseModel, EmailStr, StringConstraints, validator
from typing import List, Optional, Annotated
from datetime import datetime
from tutoring_app.database import UserRole

class UserBase(BaseModel):
    """Base user data"""
    email: EmailStr
    name: Annotated[str, StringConstraints(min_length=1, max_length=50)]

    @validator('name')
    def sanitize_name(cls, v):
        return v.strip()

class UserCreate(UserBase):
    """User creation data"""
    role: UserRole

class UserResponse(UserBase):
    """User response data"""
    id: int
    role: UserRole
    created_at: datetime
    class Config:
        orm_mode = True

class SubjectResponse(BaseModel):
    """Subject response data"""
    id: int
    name: str
    class Config:
        orm_mode = True

class ProfileResponse(BaseModel):
    """Base profile response"""
    id: int
    user_id: int
    availability: str
    bio: Optional[str]
    class Config:
        orm_mode = True

class TutorProfileCreate(BaseModel):
    """Tutor profile creation data"""
    user_id: int
    expertise: List[int]  # List of subject IDs
    hourly_rate: float
    availability: str
    bio: str
    
    @validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v < 0:
            raise ValueError('Hourly rate cannot be negative')
        return v

    class Config:
        orm_mode = True

class TutorProfileResponse(ProfileResponse):
    """Tutor profile response"""
    expertise: List[SubjectResponse]
    hourly_rate: float
    rating: Optional[float]
    total_reviews: int

class StudentProfileResponse(ProfileResponse):
    """Student profile response"""
    grade_level: str
    subjects: List[SubjectResponse]

class MessageResponse(BaseModel):
    """Message response data"""
    id: int
    chat_id: int
    sender: UserResponse
    content: str
    timestamp: datetime
    is_deleted: bool
    class Config:
        orm_mode = True

class ChatResponse(BaseModel):
    """Chat response data"""
    id: int
    student: UserResponse
    tutor: UserResponse
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    class Config:
        orm_mode = True

class AppointmentBase(BaseModel):
    """Base appointment data"""
    topic: str
    date: datetime

class AppointmentCreate(AppointmentBase):
    """Appointment creation data"""
    student_id: int
    tutor_id: int

class AppointmentResponse(AppointmentBase):
    """Appointment response data"""
    id: int
    student: UserResponse
    tutor: UserResponse
    status: str
    class Config:
        orm_mode = True

class RatingCreate(BaseModel):
    """Rating submission data"""
    rating: float
    review: str

    @validator('rating')
    def validate_rating(cls, v):
        if not 0 <= v <= 5:
            raise ValueError('Rating must be between 0 and 5')
        return v