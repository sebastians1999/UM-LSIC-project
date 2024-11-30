from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.database import get_db, TutorProfile, pwd_context, UserRole  # Added UserRole import
from routers.authentication import tutor_only, require_roles, limiter
from logger import logger

router = APIRouter()
