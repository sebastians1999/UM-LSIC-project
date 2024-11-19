from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from database import (
    Base, 
    engine, 
    SessionLocal,
    User, 
    Chat, 
    Message,
    TutorProfile,  # Added
    get_db
)

app = FastAPI()

app = FastAPI()

# Fix logging filename
logging.basicConfig(
    filename="tutor_logs.log",  # Changed from tutor_logs.log
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True  # Ensure logging is properly initialized
)

# Pydantic models
class TutorResponse(BaseModel):
    id: int
    name: str
    expertise: str
    availability: str
    hourly_rate: float
    rating: Optional[float]

class ChatRequest(BaseModel):
    tutor_id: int
    initial_message: Optional[str]

# Endpoints
@app.get("/tutors", response_model=List[TutorResponse])
def get_tutors(
    subject: Optional[str] = None,
    availability: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(User).join(User.tutor_profile).filter(User.role == "tutor")
    
    if subject:
        query = query.filter(User.tutor_profile.has(expertise=subject))
    if availability:
        query = query.filter(User.tutor_profile.has(availability=availability))
    
    tutors = query.all()
    if not tutors:
        raise HTTPException(status_code=404, detail="No tutors found matching criteria")
    
    logging.info(f"Retrieved tutors list with filters: subject={subject}, availability={availability}")
    return tutors

@app.post("/chat")
def create_chat(chat_request: ChatRequest, db: Session = Depends(get_db)):
    # Verify tutor exists
    tutor = db.query(User).filter(
        User.id == chat_request.tutor_id,
        User.role == "tutor"
    ).first()
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")

    # Get current student (assuming student_id passed through auth)
    student_id = 1  # TODO: Replace with authenticated student ID
    
    # Create chat
    new_chat = Chat(student_id=student_id, tutor_id=chat_request.tutor_id)
    db.add(new_chat)
    db.commit()
    
    # Add initial message if provided
    if chat_request.initial_message:
        message = Message(
            chat_id=new_chat.id,
            sender_id=student_id,
            content=chat_request.initial_message
        )
        db.add(message)
        db.commit()
    
    logging.info(f"Created chat {new_chat.id} between student {student_id} and tutor {chat_request.tutor_id}")
    return {"chat_id": new_chat.id}

def reset_database():
    """Reset and initialize the database with test data."""
    print("Resetting database schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    
    # Create test student
    student = User(
        role="student",
        email="test.student@example.com",
        password="testpass",
        name="Test Student"
    )
    session.add(student)
    
    # Create test tutor with profile
    tutor = User(
        role="tutor",
        email="test.tutor@example.com",
        password="testpass",
        name="Test Tutor"
    )
    session.add(tutor)
    session.commit()  # Commit to get IDs
    
    tutor_profile = TutorProfile(
        user_id=tutor.id,
        expertise="Mathematics,Physics",
        hourly_rate=50.0,
        availability="Weekdays",
        bio="Experienced math and physics tutor"
    )
    session.add(tutor_profile)
    session.commit()
    
    logging.info("Test data initialized successfully")
    return session

def test_get_tutors(session):
    print("\n[TEST] Fetching Tutors")
    tutors = session.query(User).join(User.tutor_profile).filter(User.role == "tutor").all()
    print("Request: Get Tutors")
    if tutors:
        for tutor in tutors:
            print(f"Found tutor: {tutor.name} (Expertise: {tutor.tutor_profile.expertise})")
            logging.info(f"Retrieved tutor: {tutor.name}")
    else:
        print("No tutors found")
        logging.warning("No tutors found in test")

def test_create_chat(session):
    print("\n[TEST] Creating Chat")
    student = session.query(User).filter(User.role == "student").first()
    tutor = session.query(User).filter(User.role == "tutor").first()
    
    if student and tutor:
        chat = Chat(student_id=student.id, tutor_id=tutor.id)
        session.add(chat)
        session.commit()
        print(f"Chat created between student {student.id} and tutor {tutor.id}")
        
        message = Message(
            chat_id=chat.id,
            sender_id=student.id,
            content="Hello, I need help with math"
        )
        session.add(message)
        session.commit()
        print("Initial message added to chat")
        logging.info(f"Test chat created between student {student.id} and tutor {tutor.id}")
    else:
        print("Test skipped: Missing student or tutor")
        logging.error("Test failed: Missing student or tutor data")

def main():
    print("Initializing test environment...")
    session = reset_database()
    
    print("Running tests...")
    test_get_tutors(session)
    test_create_chat(session)
    
    session.close()
    print("\nTests completed!")

if __name__ == "__main__":
    main()