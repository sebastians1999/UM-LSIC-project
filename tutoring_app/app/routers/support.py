"""
Support router handling user support requests.
Provides endpoints for contacting support with rate limiting.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.database import get_db
from routers.authentication import limiter
from auth_tools import get_current_user
from logger import logger
from schemas.authentication_schema import DecodedAccessToken
from config import get_settings

router = APIRouter(prefix='/support')
USE_REDIS = get_settings().use_redis

@router.post('/support/contact')
@limiter.limit("5/minute")
def contact_support(
    request: Request,
    message: str,
    db: Session = Depends(get_db),
    current_user: DecodedAccessToken = Depends(get_current_user)
):
    """
    Send a support message with rate limiting.

    Args:
        request (Request): The request object.
        message (str): The support message content.
        db (Session): The database session dependency.
        current_user (DecodedAccessToken): The current authenticated user.

    Returns:
        dict: A message indicating the support request has been received.

    Raises:
        HTTPException: If an error occurs while processing the support request.
    """
#TODO: Improve the contact support endpoint 
    """Send a support message with rate limiting"""
    try:
        # Log support request
        logger.info(f"Support request from user {current_user.sub}: {message}")

        # Here you would typically save to database or send email
        return {"message": "Support request received"}
    except Exception as e:
        logger.error(f"Error processing support request: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing support request")