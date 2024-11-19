from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, TutorProfile
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.patch('/availability')
def update_availability(tutor_id: int, availability: str, db: Session = Depends(get_db)):
    # Update tutor's availability
    tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == tutor_id).first()
    if not tutor_profile:
        raise HTTPException(status_code=404, detail="Tutor not found")
    tutor_profile.availability = availability
    db.commit()
    return {"message": "Availability updated"}

@router.get('/availability/{tutor_id}')
def get_availability(tutor_id: int, db: Session = Depends(get_db)):
    # Retrieve tutor's availability
    tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == tutor_id).first()
    if not tutor_profile:
        raise HTTPException(status_code=404, detail="Tutor not found")
    return {"availability": tutor_profile.availability}

@router.post('/create')
def create_tutor(user_id: int, expertise: str, hourly_rate: float, availability: str, bio: str, db: Session = Depends(get_db)):
    # Create a new tutor profile
    tutor_profile = TutorProfile(
        user_id=user_id,
        expertise=expertise,
        hourly_rate=hourly_rate,
        availability=availability,
        bio=bio,
        rating=0.0,
        total_reviews=0
    )
    db.add(tutor_profile)
    db.commit()
    db.refresh(tutor_profile)
    return {"message": "Tutor created", "tutor": tutor_profile}