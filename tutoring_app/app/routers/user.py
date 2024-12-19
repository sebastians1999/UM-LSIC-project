"""
User router handling user profile management.
Includes endpoints for updating profiles and managing user-specific data.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Union
from database.database import get_db, User, UserRole, Appointment
from auth_tools import get_current_user, require_roles
from schemas.user_schema import ProfileUpdate, StudentProfileReponse, TutorProfileResponse, UserResponse
from schemas.authentication_schema import DecodedAccessToken
from schemas.appointment_schema import AppointmentResponse
from database.redis import redis_client
import json
#hi
from config import get_settings

router = APIRouter(prefix='/users')
USE_REDIS = get_settings().use_redis

@router.put('/profile', response_model=Union[StudentProfileReponse, TutorProfileResponse])
def update_profile(request: Request, profile : ProfileUpdate, db: Session = Depends(get_db), current_user : DecodedAccessToken =Depends(require_roles(UserRole.STUDENT, UserRole.TUTOR))): 
    """
    Updates the profile of the logged in user.
    
    Parameters:
    - profile: Profile data
    - db: Database session
    - current_user: Authenticated user (student or tutor only)
    
    Returns:
    - dict: Success message
    
    Raises:
    - HTTPException(404): If user not found
    - HTTPException(403): If user not authorized
    """
    # Get the user from the database
    user : User = db.query(User).filter(User.id == current_user.sub).first()

    # Check if user exists
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.STUDENT:
        user.student_profile = profile
        response = {"user_id" : user.id, "availability" : user.student_profile.availability, "bio": user.student_profile.bio, "grade_level": user.student_profile.grade_level, "subjects": user.student_profile.subjects}
    elif user.role == UserRole.TUTOR:
        user.tutor_profile = profile
        response = {"user_id" : user.id, "availability" : user.tutor_profile.availability, "bio": user.tutor_profile.bio, "expertise": user.tutor_profile.expertise, "hourly_rate": user.tutor_profile.rate, "total_reviews": user.tutor_profile.total_reviews, "rating": user.tutor_profile.rating}
    else:
        raise HTTPException(status_code=403, detail="User must be a student or tutor to update profile.")

    db.commit()
    return response

@router.get('/profile', response_model=UserResponse)
def get_profile(
    request: Request,
    current_user: DecodedAccessToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if USE_REDIS:
        cache_key = f"profile_{current_user.sub}"
        cached_data = redis_client.get_cache(cache_key)
    if (cached_data):
        print('returning cached data (user)')
        return json.loads(cached_data)

    user = db.query(User).filter(User.id == current_user.sub).first()

    if USE_REDIS:
        redis_client.set_cache(cache_key, json.dumps(user), expiration=300)  # Cache for 5 minutes

    return user

@router.get('/{user_id}/appointments', response_model=List[AppointmentResponse])
def get_appointments(request: Request, user_id: str, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):  # Changed from int
    """Get a list of appointments for a user. Admins can view all appointments, while students and tutors can only view their own appointments."""
    if current_user.role != UserRole.ADMIN.value and current_user.sub != user_id:
        raise HTTPException(status_code=403, detail="User not authorized to view appointments")

    user = User.get_by_id(db, user_id)  # Use get_by_id method

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.STUDENT:
        appointments = db.query(Appointment).filter(Appointment.student_id == user_id).all()
    elif user.role == UserRole.TUTOR:
        appointments = db.query(Appointment).filter(Appointment.tutor_id == user_id).all()
    return appointments

@router.post('/rate', response_model=dict)
def submit_rating(request: Request, user_id: str, rating: float, review: str, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):  # Changed from int to str
    user = User.get_by_id(db, user_id)  # Using new get_by_id method
    if not user or user.role != UserRole.TUTOR:
        raise HTTPException(status_code=404, detail="Tutor not found")

    user.tutor_profile.rating = (user.tutor_profile.rating * user.tutor_profile.total_reviews + rating) / (user.tutor_profile.total_reviews + 1)
    user.tutor_profile.total_reviews += 1
    db.commit()
    return {"message": "Rating submitted"}

#TODO: someone needs to review if this is correct
@router.get('/tutors', response_model=List[TutorProfileResponse])
def get_tutors(
        request: Request,
        subjects: Union[str, None] = None,
        min_rating: Union[float, None] = None,
        max_hourly_rate: Union[float, None] = None,
        current_user: DecodedAccessToken = Depends(require_roles(UserRole.STUDENT)),
        db: Session = Depends(get_db)
    ):
        """
        Get a list of tutors based on specific filters.
        
        Parameters:
        - subjects: Filter by subjects (comma-separated string)
        - min_rating: Minimum rating of the tutor
        - max_hourly_rate: Maximum hourly rate of the tutor
        
        Returns:
        - List of tutors matching the filters
        """
        query = db.query(User).filter(User.role == UserRole.TUTOR)

        if subjects:
            subject_list = subjects.split(',')
            query = query.filter(User.tutor_profile.subjects.any(subject in subject_list for subject in User.tutor_profile.subjects))

        if min_rating:
            query = query.filter(User.tutor_profile.rating >= min_rating)

        if max_hourly_rate:
            query = query.filter(User.tutor_profile.rate <= max_hourly_rate)

        tutors = query.all()
        return tutors
