from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Union
from database.database import get_db, User, UserRole, Appointment
from auth_tools import get_current_user, require_roles
from schemas.user_schema import ProfileUpdate, StudentProfileReponse, TutorProfileResponse
from schemas.authentication_schema import DecodedAccessToken
from schemas.appointment_schema import AppointmentResponse

router = APIRouter(prefix='/users')

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

@router.get('/{user_id}/appointments', response_model=List[AppointmentResponse])
def get_appointments(request: Request, user_id: int, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a list of appointments for a user. Admins can view all appointments, while students and tutors can only view their own appointments."""
    if current_user.role != UserRole.ADMIN.value and current_user.sub != user_id:
        raise HTTPException(status_code=403, detail="User not authorized to view appointments")

    # Fetch a list of user's scheduled appointments
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.STUDENT:
        appointments = db.query(Appointment).filter(Appointment.student_id == user_id).all()
    elif user.role == UserRole.TUTOR:
        appointments = db.query(Appointment).filter(Appointment.tutor_id == user_id).all()
    return appointments

@router.post('/rate', response_model=dict)
def submit_rating(request: Request, user_id: int, rating: float, review: str, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    # Ensure the user exists
    user = db.query(User).filter(User.id == user_id, User.role == UserRole.TUTOR).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Submit a rating and review for a user
    user.tutor_profile.rating = (user.tutor_profile.rating * user.tutor_profile.total_reviews + rating) / (user.tutor_profile.total_reviews + 1)
    user.tutor_profile.total_reviews += 1
    db.commit()
    return {"message": "Rating submitted"}
