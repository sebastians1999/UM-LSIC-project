from fastapi import APIRouter, Depends, HTTPException , Request
from sqlalchemy.orm import Session
from datetime import datetime
from database.database import get_db, User, UserRole, Appointment
from auth_tools import get_current_user
from schemas.appointment_schema import AppointmentResponse
from schemas.authentication_schema import DecodedAccessToken
from database.redis import redis_client
import json
#hi
from tutoring_app.app.config import get_settings

# Check if we should use Redis
USE_REDIS = get_settings().use_redis
router = APIRouter(prefix='/appointments')

### The way I want to set up appointments is as follows:
### - A user (student or tutor) can schedule a meeting with another user
###      by providing the other user's ID, the topic of the meeting, and the date.
### - The meeting is then added to the database with a status of "pending".
### - The other user can then accept or reject the meeting by making a request to
###      the appropriate endpoint with the meeting id.

@router.post('/', response_model=AppointmentResponse)
def schedule_meeting(request: Request, other_user_id: int, topic: str, date: datetime, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    # Ensure the target user exists
    target = db.query(User).filter(User.id == other_user_id).first()

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == UserRole.STUDENT.value:
        # Check if the student is scheduling a meeting with a tutor
        if target.role != UserRole.TUTOR:
            raise HTTPException(status_code=403, detail="Students can only schedule meetings with tutors")
        student_id = current_user.sub
        tutor_id = other_user_id
    elif current_user.role == UserRole.TUTOR.value:
        # Check if the tutor is scheduling a meeting with a student
        if target.role != UserRole.STUDENT:
            raise HTTPException(status_code=403, detail="Tutors can only schedule meetings with students")
        student_id = other_user_id
        tutor_id = current_user.sub
    else:
        raise HTTPException(status_code=403, detail="User must be a student or tutor to schedule a meeting")

    # Schedule a new meeting between a student and a tutor
    appointment = Appointment(
        student_id=student_id,
        tutor_id=tutor_id,
        topic=topic,
        date=date,
        status="pending"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment

@router.get('/approve/{meetingID}', response_model=AppointmentResponse)
def approve_meeting(request: Request, meetingID: int, db: Session = Depends(get_db), current_user: DecodedAccessToken = Depends(get_current_user)):
    # Approve a meeting request
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if current_user.sub == appointment.created_by:
        raise HTTPException(status_code=403, detail="User cannot approve their own meeting")

    if current_user.role == UserRole.STUDENT.value and appointment.student_id != current_user.sub:
        raise HTTPException(status_code=403, detail="User not authorized to approve meeting")
    if current_user.role == UserRole.TUTOR.value and appointment.tutor_id != current_user.sub:
        raise HTTPException(status_code=403, detail="User not authorized to approve meeting")

    appointment.status = "scheduled"
    db.commit()
    return appointment

@router.get('/reject/{meetingID}', response_model=AppointmentResponse)
def reject_meeting(request: Request, meetingID: int, db: Session = Depends(get_db), current_user: DecodedAccessToken = Depends(get_current_user)):
    # Reject a meeting request
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if current_user.sub == appointment.created_by:
        raise HTTPException(status_code=403, detail="User cannot reject their own meeting")

    if current_user.role == UserRole.STUDENT.value and appointment.student_id != current_user.sub:
        raise HTTPException(status_code=403, detail="User not authorized to reject meeting")
    if current_user.role == UserRole.TUTOR.value and appointment.tutor_id != current_user.sub:
        raise HTTPException(status_code=403, detail="User not authorized to reject meeting")

    appointment.status = "rejected"
    db.commit()
    return appointment

@router.get('/{meetingID}', response_model=AppointmentResponse)
def get_meeting(
    request: Request,
    meetingID: int,
    current_user: DecodedAccessToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cache_key = f"appointment_{meetingID}"
    cached_data = redis_client.get_cache(cache_key)
    if cached_data:
        print('returning cached data (Appointments)')
        return json.loads(cached_data)

    # Fetch details about a specific meeting
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()

    # Check if the user is authorized to view the meeting
    if current_user.role != UserRole.ADMIN.value:
        if current_user.role == UserRole.STUDENT.value and appointment.student_id != current_user.sub:
            raise HTTPException(status_code=403, detail="User not authorized to view meeting")  
        if current_user.role == UserRole.TUTOR.value and appointment.tutor_id != current_user.sub:
            raise HTTPException(status_code=403, detail="User not authorized to view meeting")

    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")

    redis_client.set_cache(cache_key, json.dumps(appointment), expiration=600)  # Cache for 10 minutes

    return appointment

@router.patch('/update/{meetingID}', response_model=AppointmentResponse)
def update_meeting(request: Request, meetingID: int, topic: str = None, date: datetime = None, status: str = None, current_user:DecodedAccessToken=Depends(get_current_user), db: Session = Depends(get_db)):
    # Update details of a specific meeting
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()

    # Check if the user is authorized to update the meeting
    if current_user.role != UserRole.ADMIN.value:
        if current_user.role == UserRole.STUDENT.value and appointment.student_id != current_user.sub:
            raise HTTPException(status_code=403, detail="User not authorized to update meeting")  
        if current_user.role == UserRole.TUTOR.value and appointment.tutor_id != current_user.sub:
            raise HTTPException(status_code=403, detail="User not authorized to update meeting")

    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if topic:
        appointment.topic = topic
    if date:
        appointment.date = date
    if status:
        appointment.status = status

    # Meeting status is now "pending" after updating
    appointment.status = "pending"

    db.commit()
    return appointment

@router.delete('/cancel/{meetingID}', response_model=AppointmentResponse)
def cancel_meeting(request: Request, meetingID: int, current_user:DecodedAccessToken=Depends(get_current_user), db: Session = Depends(get_db)):
    # Cancel a specific meeting
    appointment = db.query(Appointment).filter(Appointment.id == meetingID).first()

    # Check if the user is authorized to cancel the meeting
    if current_user.role != UserRole.ADMIN.value:
        if current_user.role == UserRole.STUDENT.value and appointment.student_id != current_user.sub:
            raise HTTPException(status_code=403, detail="User not authorized to cancel meeting")  
        if current_user.role == UserRole.TUTOR.value and appointment.tutor_id != current_user.sub:
            raise HTTPException(status_code=403, detail="User not authorized to cancel meeting")

    if not appointment:
        raise HTTPException(status_code=404, detail="Meeting not found")

    appointment.status = "cancelled"
    db.commit()
    return appointment