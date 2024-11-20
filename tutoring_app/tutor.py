from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, TutorProfile, pwd_context
from models import TutorProfileResponse
from authentication import tutor_only, require_roles, limiter
from logger import logger

router = APIRouter()

@router.patch('/availability')
@limiter.limit("10/minute")
def update_availability(tutor_id: int, availability: str, db: Session = Depends(get_db), _=Depends(tutor_only)):
    """
    Update a tutor's availability schedule.

    Parameters:
    - tutor_id: ID of the tutor
    - availability: New availability string
    - db: Database session
    - _: Tutor role verification

    Returns:
    - dict: Success message
    
    Raises:
    - HTTPException(404): If tutor not found
    - HTTPException(500): If update fails
    """
    try:
        # Update tutor's availability
        tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == tutor_id).first()
        if not tutor_profile:
            raise HTTPException(status_code=404, detail="Tutor not found")
        tutor_profile.availability = availability
        db.commit()
        return {"message": "Availability updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tutor {tutor_id} availability: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while updating availability")

@router.get('/availability/{tutor_id}')
@limiter.limit("10/minute")
def get_availability(tutor_id: int, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.STUDENT, UserRole.TUTOR))):
    """
    Retrieve a tutor's availability schedule.

    Parameters:
    - tutor_id: ID of the tutor
    - db: Database session
    - _: Role verification (Student or Tutor)

    Returns:
    - dict: Tutor's availability
    
    Raises:
    - HTTPException(404): If tutor not found
    """
    # Retrieve tutor's availability
    tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == tutor_id).first()
    if not tutor_profile:
        raise HTTPException(status_code=404, detail="Tutor not found")
    return {"availability": tutor_profile.availability}

@router.post('/create', response_model=TutorProfileResponse)
@limiter.limit("10/minute")
def create_tutor(profile_data: TutorProfileCreate, db: Session = Depends(get_db)):
    """
    Create a new tutor profile.

    Parameters:
    - profile_data: Data for creating a new tutor profile
    - db: Database session

    Returns:
    - dict: Success message and tutor profile
    
    Raises:
    - HTTPException(500): If creation fails
    """
    try:
        # Create a new tutor profile
        tutor_profile = TutorProfile(
            user_id=profile_data.user_id,
            expertise=profile_data.expertise,
            hourly_rate=profile_data.hourly_rate,
            availability=profile_data.availability,
            bio=profile_data.bio,
            rating=0.0,
            total_reviews=0
        )
        db.add(tutor_profile)
        db.commit()
        db.refresh(tutor_profile)
        return {"message": "Tutor created", "tutor": tutor_profile}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tutor profile for user {profile_data.user_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while creating tutor profile")