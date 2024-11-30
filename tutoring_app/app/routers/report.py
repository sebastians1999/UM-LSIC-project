from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.database import get_db, UserReport, MessageReport, User, Message
from auth_tools import get_current_user
from schemas.authentication_schema import DecodedAccessToken
from schemas.report_schema import ReportMessage, ReportUser

router = APIRouter('report')

@router.post('/message/{messageID}')
def report_message(report: ReportMessage, current_user:DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    # Report a specific message in a chat
    message = db.query(Message).filter(Message.id == report.message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Create a report for the message
    message_report = MessageReport(
        message_id=report.message_id,
        reason=report.reason,
        by=current_user.sub 
    )

    message.is_deleted = True

    db.add(message_report)
    db.commit()
    db.refresh(message_report)
    return {**report.model_dump(), "id": message_report.id, "message": f"Message {report.message_id} reported"}

@router.post('/user/{userID}')
def report_user(report: ReportUser, current_user:DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == report.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create a report for the user
    user_report = UserReport(
        user_id=report.user_id,
        reason=report.reason,
        by=current_user.sub
    )

    db.add(user_report)
    db.commit()
    db.refresh(user_report)
    return {**report.model_dump(), "id": user_report.id, "message": f"User {report.user_id} reported"}