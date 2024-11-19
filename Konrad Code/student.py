from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, TutorProfile, Chat
from datetime import datetime
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import List

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ChatResponse(BaseModel):
    id: int
    student_id: int
    tutor_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

@router.get('/tutors')
def get_tutors(subject: str = None, availability: str = None, db: Session = Depends(get_db)):
    # Fetch available tutors
    query = db.query(TutorProfile)
    if subject:
        query = query.filter(TutorProfile.expertise.contains(subject))
    if availability:
        query = query.filter(TutorProfile.availability.contains(availability))
    tutors = query.all()
    return {"tutors": tutors}

@router.get('/tutors/{tutor_id}')
def get_tutor(tutor_id: int, db: Session = Depends(get_db)):
    # Retrieve tutor details
    tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == tutor_id).first()
    if not tutor_profile:
        raise HTTPException(status_code=404, detail="Tutor not found")
    return {"tutor": tutor_profile}

@router.post('/chat', response_model=ChatResponse)
def create_chat(student_id: int, tutor_id: int, db: Session = Depends(get_db)):
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