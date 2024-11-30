from pydantic import BaseModel, EmailStr, StringConstraints, field_validator
from typing import Annotated, Optional, List
from database.database import UserRole
from bleach import clean
from datetime import datetime

############################
### USER ACCOUNT SCHEMAS ###
############################

class UserBase(BaseModel):
    """Base user data"""
    email: EmailStr
    # Add constraints to name field (min length: 1, max length: 50)
    name: Annotated[str, StringConstraints(min_length=1, max_length=50)]

    @field_validator('name')
    def sanitize_name(cls, v):
        return clean(v, strip=True)

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

############################
##### SUBJECT SCHEMAs ######
############################

class SubjectBase(BaseModel):
    """Base subject data"""
    name: str

    @field_validator('name')
    def sanitize_name(cls, v):
        return clean(v)

class SubjectResponse(SubjectBase):
    """Subject response data"""
    id: int
    class Config:
        orm_mode = True

############################
##### PROFILE SCHEMAS ######
############################

class ProfileBase(BaseModel):
    """Base profile data"""
    user_id: int
    availability: str
    bio: Optional[str]

    @field_validator('bio')
    def sanitize_bio(cls, v):
        return clean(v)

class ProfileResponse(ProfileBase):
    """Profile response data"""
    id: int
    class Config:
        orm_mode = True

class ProfileCreate(ProfileBase):
    """Profile creation data"""
    pass # Same as ProfileBase, no additional fields

class ProfileUpdate(ProfileBase):
    """Profile update data"""
    pass # Same as ProfileBase, no additional fields

class TutorProfileCreate(ProfileBase):
    """Tutor profile data"""
    expertise: list[int] # List of subject IDs
    hourly_rate: float

    @field_validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v < 0:
            raise ValueError('Hourly rate cannot be negative')
        return v

    class Config:
        orm_mode = True

class TutorProfileResponse(ProfileResponse):
    """Tutor profile response"""
    expertise: list[SubjectResponse]
    hourly_rate: float
    rating: Optional[float]
    total_reviews: int

class StudentProfileReponse(ProfileResponse):
    """Student profile response"""
    grade_level: str
    subjects: List[SubjectResponse]