from typing import List, Any
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from logger import logger
from database.database import UserRole
from schemas.authentication_schema import DecodedAccessToken
from config import get_settings
import requests
import os

# CONSTANTS
GITLAB_API_URL = get_settings().gitlab_api_url
SECRET_KEY = get_settings().secret_key
ALGORITHM = get_settings().hash_algorithm

# security scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

##################################
### AUTHORIZATION DEPENDENCIES ###
##################################

def get_current_user(token: str = Depends(oauth2_scheme)) -> DecodedAccessToken:
    """
    Get the current user from the token.
    
    Args:
    - token (str): The user's token
    
    Returns:
    - dict: The user's data
    """
    try:
        payload : dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if not payload.get("id"):
            raise HTTPException(status_code=401, detail="Invalid token. Missing user ID.")
        
        if payload.get("refresh"):
            raise HTTPException(status_code=401, detail="Invalid token. Refresh token provided.")
        
        if payload.get("logged_in") is False:
            raise HTTPException(status_code=401, detail="User is not logged in.")
        
        return DecodedAccessToken(**payload)

    except JWTError as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token. Could not decode token.")

def verify_user_role(user: DecodedAccessToken, allowed_roles: List[UserRole]) -> DecodedAccessToken:
    """
    Verify that the user has the required role.
    
    Args:
    - user (dict): The user's data
    - allowed_roles (list): List of allowed roles
    
    Returns:
    - None
    """
    if not user or user['role'] not in [role.value for role in allowed_roles]:
        raise HTTPException(status_code=403,
                            detail=f"User must have one of these roles: {[role.value for role in allowed_roles]}")
    
    return user

def require_roles(*roles: UserRole) -> DecodedAccessToken:
    def dependency(current_user: DecodedAccessToken = Depends(get_current_user)) -> DecodedAccessToken:
        return verify_user_role(current_user, roles)
    return dependency

def student_only(current_user: DecodedAccessToken = Depends(get_current_user)) -> DecodedAccessToken:
    """Verify that the user is a student"""
    return verify_user_role(current_user, [UserRole.STUDENT])

def tutor_only(current_user: DecodedAccessToken = Depends(get_current_user)) -> DecodedAccessToken:
    """Verify that the user is a tutor """
    return verify_user_role(current_user, [UserRole.TUTOR])

def admin_only(current_user: DecodedAccessToken = Depends(get_current_user)) -> DecodedAccessToken:
    """Verify that the user is an admin """
    return verify_user_role(current_user, [UserRole.ADMIN])