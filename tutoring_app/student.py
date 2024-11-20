from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, TutorProfile, Chat, pwd_context
from datetime import datetime
from pydantic import BaseModel
from typing import List
from authentication import student_only, require_roles, limiter
from logger import logger
from models import ChatResponse, TutorProfileResponse

router = APIRouter()

@router.get('/tutors/{tutor_id}', response_model=TutorProfileResponse)
@limiter.limit("10/minute")
def get_tutor(tutor_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific tutor.

    Parameters:
    - tutor_id: ID of the tutor to retrieve
    - db: Database session
    - _: Student role verification

    Returns:
    - dict: Tutor profile information
    
    Raises:
    - HTTPException(404): If tutor not found
    """
    # Retrieve tutor details
    tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == tutor_id).first()
    if not tutor_profile:
        raise HTTPException(status_code=404, detail="Tutor not found")
    return {"tutor": tutor_profile}

@router.get('/tutors')
@limiter.limit("10/minute")
def get_tutors(subject: str = None, availability: str = None, db: Session = Depends(get_db), _=Depends(student_only)):
    """
    Retrieve a list of available tutors with optional filtering.

    Parameters:
    - subject (optional): Filter tutors by subject expertise
    - availability (optional): Filter tutors by availability
    - db: Database session
    - _: Student role verification

    Returns:
    - dict: List of matching tutors
    
    Raises:
    - HTTPException(500): If database error occurs
    """
    try:
        # Fetch available tutors
        query = db.query(TutorProfile)
        if subject:
            query = query.filter(TutorProfile.expertise.contains(subject))
        if availability:
            query = query.filter(TutorProfile.availability.contains(availability))
        tutors = query.all()
        return {"tutors": tutors}
    except Exception as e:
        logger.error(f"Error fetching tutors - subject: {subject}, availability: {availability}: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving tutors")

@router.post('/chat', response_model=ChatResponse)
@limiter.limit("10/minute")
def create_chat(student_id: int, tutor_id: int, db: Session = Depends(get_db), _=Depends(student_only)):
    """
    Create a new chat session between a student and tutor.

    Parameters:
    - student_id: ID of the student
    - tutor_id: ID of the tutor
    - db: Database session
    - _: Student role verification

    Returns:
    - ChatResponse: Created chat session details
    
    Raises:
    - HTTPException(500): If creation fails
    """
    try:
        # Create a new chat session with a tutor
        chat = Chat(
            student_id=student_id,
            tutor_id=tutor_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat between student {student_id} and tutor {tutor_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while creating chat")