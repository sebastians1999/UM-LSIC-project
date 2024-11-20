from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import (
    UserCreate, UserResponse, MessageResponse, ChatResponse,
    AppointmentCreate, AppointmentResponse, RatingCreate
)
from authentication import require_roles, admin_only, limiter
from utilities import get_user_by_id, get_chat_with_messages, get_user_chats

router = APIRouter()

class UserCreateRequest(BaseModel):
    email: EmailStr
    name: constr(min_length=1, max_length=50)
    password: constr(min_length=8)
    
    @validator('name')
    def sanitize_name(cls, v):
        return bleach.clean(v)

# Authentication Dependency
def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user

# Admin Dependency
def get_admin_user(user = Depends(get_current_user)):
    if user['role'] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Unauthorized to access this endpoint")
    return user

# Notice the Depends(get_current_user) in the function signature
# This is a dependency that ensures the user is authenticated before accessing the endpoint
# Other endpoints can use this dependency to ensure the user is authenticated
@router.post('/users/verify')
@limiter.limit("10/minute")
def verify_user(request : Request, db : Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Verify and register a new user after OAuth login.
    
    Parameters:
    - request: The incoming request containing session data
    - db: Database session
    - current_user: Currently authenticated user from OAuth
    
    Returns:
    - dict: User information and registration status
    
    Raises:
    - HTTPException(401): If user is not authenticated
    """
    # The user should already have been authenticated by accessing the /auth/login endpoint
    # after which the user information is securely stored in the session.
    # This endpoint is used to verify whether the user is already registered in the database.
    # This endpoint gets redirected to from /auth/callback after the user logs in with GitLab.

    # Check if the user is already registered (by email)
    existing_user = db.query(User).filter(User.email == current_user['email']).first()
    if existing_user:
        # Store the user ID in the session
        request.session['user']['id'] = existing_user.id
        return {"message": "User logged in", "user": existing_user}
    
    # Register a new user
    user = User(
        email=user['email'],
        role=user['role'], # 'admin', 'student', 'tutor'
        name=user['name'],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Store the user ID in the session
    request.session['user']['id'] = user.id

    return {"message": "User registered", "user": user}

@router.put('/users/profile')
def update_profile(bio: str, db: Session = Depends(get_db), current_user=Depends(require_roles(UserRole.STUDENT, UserRole.TUTOR))): 
    """
    Update user profile information.
    
    Parameters:
    - bio: New biography text
    - db: Database session
    - current_user: Authenticated user (student or tutor only)
    
    Returns:
    - dict: Success message
    
    Raises:
    - HTTPException(404): If user not found
    - HTTPException(403): If user not authorized
    """
    # Create or update user profile
    user = db.query(User).filter(User.id == current_user['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.STUDENT:
        user.student_profile.bio = bio
    elif user.role == UserRole.TUTOR:
        user.tutor_profile.bio = bio
    db.commit()
    return {"message": "Profile updated"}

# For now I am only allowing admins to view user information
# This can be changed, maybe we should return limited information for non-admin users
@router.get('/users/{id}', response_model=UserResponse)
@limiter.limit("10/minute")
def get_user(id: int, db: Session = Depends(get_db)):
    return {"user": get_user_by_id(db, id)}

@router.get('/users')
def get_all_users(db: Session = Depends(get_db), _=Depends(admin_only)):
    # Retrieve all users
    users = db.query(User).all()
    return {"users": users}

@router.get('/chats', response_model=List[ChatResponse])
def get_chats(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_id(db, current_user['id'])
    chats = get_user_chats(db, user.id, user.role)
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
    return get_chat_with_messages(db, chatID)

@router.post('/chats/{chatID}/messages', response_model=MessageResponse)
def send_message(chatID: int, sender_id: int, content: str, db: Session = Depends(get_db)):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message in chat {chatID}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while sending message")

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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving meetings for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving meetings")

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
@limiter.limit("5/minute")
def contact_support(
    message: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Send a support message with rate limiting"""
    try:
        # Log support request
        logger.info(f"Support request from user {current_user['id']}: {message}")
        # Here you would typically save to database or send email
        return {"message": "Support request received"}
    except Exception as e:
        logger.error(f"Error processing support request: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing support request")

@router.delete('/users/{userID}')
@limiter.limit("3/minute")
def delete_user(
    userID: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_only)
):
    """Delete user with admin authentication and logging"""
    try:
        user = db.query(User).filter(User.id == userID).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"User {userID} deleted by admin {current_user['id']}")
        db.delete(user)
        db.commit()
        return {"message": f"User {userID} deleted"}
    except Exception as e:
        logger.error(f"Error deleting user {userID}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting user")

@router.post('/users/create')
@limiter.limit("3/minute")
def create_user(user_data: UserCreateRequest, db: Session = Depends(get_db)):
    """Create a new user with validation"""
    # Check if user already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate password strength
    if not verify_password_strength(user_data.password):
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 12 characters and contain uppercase, lowercase, numbers, and special characters"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    user.set_password(user_data.password)
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created: {user.email}")
        return {"message": "User created successfully", "user_id": user.id}
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating user")