"""
Report router handling user and message reporting functionality.
Allows users to report inappropriate content or users for admin review.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Union
from database.database import get_db, UserReport, MessageReport, User, Message
from auth_tools import get_current_user
from schemas.authentication_schema import DecodedAccessToken
from schemas.report_schema import ReportMessage, ReportUser
from config import get_settings

router = APIRouter(prefix='/report')
USE_REDIS = get_settings().use_redis

@router.post('/message/{messageID}')
def report_message(request: Request, report: ReportMessage, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Report a message by its ID.
    Args:
        request (Request): The HTTP request object.
        report (ReportMessage): The report details containing the message ID and reason.
        current_user (DecodedAccessToken, optional): The current authenticated user. Defaults to Depends(get_current_user).
        db (Session, optional): The database session. Defaults to Depends(get_db).
    Raises:
        HTTPException: If the message with the given ID is not found.
    Returns:
        dict: A dictionary containing the report details and the ID of the created message report.
    """
    message = db.query(Message).filter(Message.id == report.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message_report = MessageReport(
        message_id=report.message_id,
        reason=report.reason,
        by=current_user.sub
    )

    db.add(message_report)
    db.commit()
    db.refresh(message_report)
    return {**report.model_dump(), "id": message_report.id, "message": f"Message {report.message_id} reported"}

@router.post('/user/{userID}')
def report_user(request: Request, report: ReportUser, current_user: DecodedAccessToken = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Report a user for a specific reason.
    Args:
        request (Request): The HTTP request object.
        report (ReportUser): The report details including user_id and reason.
        current_user (DecodedAccessToken, optional): The current authenticated user. Defaults to Depends(get_current_user).
        db (Session, optional): The database session. Defaults to Depends(get_db).
    Raises:
        HTTPException: If the user to be reported is not found.
    Returns:
        dict: A dictionary containing the report details, report ID, and a message indicating the user has been reported.
    """
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