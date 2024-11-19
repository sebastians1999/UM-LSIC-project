from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db, User, Chat, Message, Appointment, UserRole
from datetime import datetime
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import joinedload


router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    name: str

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender: Optional[UserResponse]
    content: str
    timestamp: datetime
    is_deleted: bool

    class Config:
        orm_mode = True

class ChatResponse(BaseModel):
    id: int
    student: Optional[UserResponse]
    tutor: Optional[UserResponse]
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        orm_mode = True

@router.post('/users/register')
def register_user(email: str, password: str, role: UserRole, name: str, db: Session = Depends(get_db)):
    # Check if the email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Register a new user
    user = User(
        email=email,
        password=pwd_context.hash(password),  # Replace with actual hashed password
        role=role,
        name=name,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered", "user": user}

@router.put('/users/profile')
def update_profile(user_id: int, bio: str, db: Session = Depends(get_db)):
    # Create or update user profile
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.STUDENT:
        user.student_profile.bio = bio
    elif user.role == UserRole.TUTOR:
        user.tutor_profile.bio = bio
    db.commit()
    return {"message": "Profile updated"}

@router.get('/users/{id}')
def get_user(id: int, db: Session = Depends(get_db)):
    # Retrieve user information
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}

@router.get('/users')
def get_all_users(db: Session = Depends(get_db)):
    # Retrieve all users
    users = db.query(User).all()
    return {"users": users}

@router.get('/chats', response_model=List[ChatResponse])
def get_chats(user_id: int, db: Session = Depends(get_db)):
    # List all active chats for the logged-in user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    chats = []
    if user.role == UserRole.STUDENT:
        chats = db.query(Chat).filter(Chat.student_id == user_id).all()
    elif user.role == UserRole.TUTOR:
        chats = db.query(Chat).filter(Chat.tutor_id == user_id).all()
    detailed_chats = []
    for chat in chats:
        detailed_chats.append({
            "id": chat.id,
            "student": {
                "id": chat.student.id,
                "email": chat.student.email,
                "role": chat.student.role,
                "name": chat.student.name
            },
            "tutor": {
                "id": chat.tutor.id,
                "email": chat.tutor.email,
                "role": chat.tutor.role,
                "name": chat.tutor.name
            },
            "created_at": chat.created_at,
            "updated_at": chat.updated_at
        })
    return detailed_chats

@router.get('/chats/{chatID}', response_model=ChatResponse)
def get_chat(chatID: int, db: Session = Depends(get_db)):
    # Fetch chat with related users and messages eagerly loaded
    chat = db.query(Chat).options(
        joinedload(Chat.student),
        joinedload(Chat.tutor),
        joinedload(Chat.messages).joinedload(Message.sender)
    ).filter(Chat.id == chatID).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    # Verify relations are loaded
    if not chat.student or not chat.tutor:
        raise HTTPException(status_code=404, detail="Chat has invalid student or tutor reference")
    
    return chat

@router.post('/chats/{chatID}/messages', response_model=MessageResponse)
def send_message(chatID: int, sender_id: int, content: str, db: Session = Depends(get_db)):
    # Ensure the sender exists
    sender = db.query(User).filter(User.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    # Send a message in an existing chat
    message = Message(
        chat_id=chatID,
        sender_id=sender_id,
        content=content,
        timestamp=datetime.now()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

@router.post('/reports/messages/{chatID}/{messageID}')
def report_message(chatID: int, messageID: int, db: Session = Depends(get_db)):
    # Report a specific message in a chat
    message = db.query(Message).filter(Message.id == messageID, Message.chat_id == chatID).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_deleted = True
    db.commit()
    return {"message": f"Message {messageID} in chat {chatID} reported"}

@router.get('/users/{user_id}/appointments')
def get_appointments(user_id: int, db: Session = Depends(get_db)):
    # Fetch a list of user's scheduled appointments
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.STUDENT:
        appointments = db.query(Appointment).filter(Appointment.student_id == user_id).all()
    elif user.role == UserRole.TUTOR:
        appointments = db.query(Appointment).filter(Appointment.tutor_id == user_id).all()
    return {"appointments": appointments}

@router.post('/meetings')
def schedule_meeting(student_id: int, tutor_id: int, topic: str, date: datetime, db: Session = Depends(get_db)):
    # Ensure the student and tutor exist
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    tutor = db.query(User).filter(User.id == tutor_id, User.role == UserRole.TUTOR).first()
    if not student or not tutor:
        raise HTTPException(status_code=404, detail="Student or Tutor not found")
    
    # Schedule a new meeting between a student and a tutor
    appointment = Appointment(
        student_id=student_id,
        tutor_id=tutor_id,
        topic=topic,
        date=date,
        status="scheduled"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return {"message": "Meeting scheduled", "appointment": appointment}

@router.get('/meetings')
def get_current_meetings(user_id: int, current: bool = False, db: Session = Depends(get_db)):
    # Retrieve all current meetings for the logged-in user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    appointments = []
    if user.role == UserRole.STUDENT:
        appointments = db.query(Appointment).filter(Appointment.student_id == user_id).all()
    elif user.role == UserRole.TUTOR:
        appointments = db.query(Appointment).filter(Appointment.tutor_id == user_id).all()
    if current:
        appointments = [appt for appt in appointments if appt.status == "scheduled"]
    return {"meetings": appointments}

@router.get('/meetings/{meetingID}')
def get_meeting(meetingID: int, db: Session = Depends(get_db)):
    # Fetch details about a specific meeting
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"meeting": appointment}

@router.patch('/meetings/{meetingID}')
def update_meeting(meetingID: int, topic: str = None, date: datetime = None, status: str = None, db: Session = Depends(get_db)):
    # Update details of a specific meeting
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if topic:
        appointment.topic = topic
    if date:
        appointment.date = date
    if status:
        appointment.status = status
    db.commit()
    return {"message": f"Meeting {meetingID} updated"}

@router.delete('/meetings/{meetingID}')
def cancel_meeting(meetingID: int, db: Session = Depends(get_db)):
    # Cancel a specific meeting
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")
    appointment.status = "cancelled"
    db.commit()
    return {"message": f"Meeting {meetingID} cancelled"}

@router.post('/ratings')
def submit_rating(user_id: int, rating: float, review: str, db: Session = Depends(get_db)):
    # Ensure the user exists
    user = db.query(User).filter(User.id == user_id, User.role == UserRole.TUTOR).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Submit a rating and review for a user
    user.tutor_profile.rating = (user.tutor_profile.rating * user.tutor_profile.total_reviews + rating) / (user.tutor_profile.total_reviews + 1)
    user.tutor_profile.total_reviews += 1
    db.commit()
    return {"message": "Rating submitted"}

@router.post('/support/contact')
def contact_support(user_id: int, message: str, db: Session = Depends(get_db)):
    # Send a message to the admin for support
    # Logic to send support message (e.g., save to database, send email, etc.)
    return {"message": "Support message sent"}

@router.delete('/users/{userID}')
def delete_user(userID: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"User {userID} deleted"}