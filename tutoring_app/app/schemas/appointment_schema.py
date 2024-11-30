from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from bleach import clean

class AppointmentBase(BaseModel):
    """Base appointment data. An appointment is a scheduled meeting between a student and tutor."""
    topic: str
    date: datetime
    duration: int # Duration in minutes

    @field_validator('topic')
    def sanitize_topic(cls, v):
        return clean(v)
    
    @field_validator('duration')
    def validate_duration(cls, v):
        if v < 0:
            raise ValueError('Duration cannot be negative')
        return v

class AppointmentCreate(AppointmentBase):
    """Appointment creation data"""
    student_id: int
    tutor_id: int

class AppointmentReponse(AppointmentBase):
    """Appointment response data"""
    id: int
    student_id: int
    tutor_id: int
    student_name: str
    tutor_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class RatingBase(BaseModel):
    """Base rating data"""
    rating: int
    review: Optional[str] = None # Review is optional

    @field_validator('review')
    def sanitize_review(cls, v):
        return clean(v)

    @field_validator('rating')
    def validate_rating(cls, v):
        if v < 0 or v > 5:
            raise ValueError('Rating must be between 0 and 5')
        return v