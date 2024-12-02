from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, Enum, Index, CheckConstraint, Table
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
import uuid
from passlib.context import CryptContext
from config import get_settings
import enum
import re
from typing import Optional

"""
Database models for the tutoring platform.
Includes models for users, profiles, chats, messages, and appointments.
Uses SQLAlchemy ORM with PostgreSQL/SQLite backend.
"""

# Base class for ORM models
Base = declarative_base()

# Enum for user roles
class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    STUDENT = "STUDENT"
    TUTOR = "TUTOR"

def is_valid_uuid(uuid_str: str) -> bool:
    """Validate UUID string format."""
    if not uuid_str:
        return False
    try:
        # Validate length and format
        if len(uuid_str) != 36:
            return False
        # Try to parse as UUID to validate format
        uuid_obj = uuid.UUID(uuid_str)
        return str(uuid_obj) == uuid_str.lower()
    except (ValueError, AttributeError, TypeError):
        return False

def generate_uuid() -> str:
    """Generate a string UUID."""
    return str(uuid.uuid4()).lower()

# Subject Model for normalized subject storage
class Subject(Base):
    """Represents academic subjects that can be taught/studied."""
    __tablename__ = 'subjects'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    
    def __repr__(self):
        return f"<Subject(id={self.id}, name={self.name})>"

# Junction table for student-subject relationship
student_subjects = Table('student_subjects', Base.metadata,
    Column('student_profile_id', String(36), ForeignKey('student_profiles.id', ondelete='CASCADE'), primary_key=True),
    Column('subject_id', String(36), ForeignKey('subjects.id', ondelete='CASCADE'), primary_key=True)
)

# Junction table for tutor-expertise relationship
tutor_expertise = Table('tutor_expertise', Base.metadata,
    Column('tutor_profile_id', String(36), ForeignKey('tutor_profiles.id', ondelete='CASCADE'), primary_key=True),
    Column('subject_id', String(36), ForeignKey('subjects.id', ondelete='CASCADE'), primary_key=True)
)

# User Model
class User(Base):
    """User model with role-based access control and profile relationships."""
    __tablename__ = 'users'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    role = Column(Enum(UserRole), nullable=False)  # Use Enum for role
    email = Column(String(255), unique=True, nullable=False, index=True)  # Email should be unique and indexed
    #password = Column(String(255), nullable=False)  # Store hashed passwords
    name = Column(String(100), nullable=False)  # Added length constraint
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    is_banned_until = Column(DateTime, nullable=True)  # Nullable field for ban duration
    #reports = relationship("UserReport", back_populates="user")

    # Relationships
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    tutor_profile = relationship("TutorProfile", back_populates="user", uselist=False)
    chats_as_student = relationship(
        "Chat",
        primaryjoin="User.id==Chat.student_id",
        back_populates="student",
        foreign_keys='Chat.student_id',
        cascade='all, delete-orphan'
    )
    chats_as_tutor = relationship(
        "Chat",
        primaryjoin="User.id==Chat.tutor_id",
        back_populates="tutor",
        foreign_keys='Chat.tutor_id',
        cascade='all, delete-orphan'
    )
    messages_sent = relationship(
        "Message",
        back_populates="sender",
        foreign_keys='Message.sender_id',
        cascade='all, delete-orphan'
    )

    @classmethod
    def get_by_id(cls, db, user_id: str) -> Optional['User']:
        """Get user by UUID string."""
        if not is_valid_uuid(user_id):
            return None
        return db.query(cls).filter(cls.id == user_id).first()
    
    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return str(self.id)

    #def set_password(self, password: str):
        #"""Hash and set the user's password."""
        #self.password = pwd_context.hash(password)

    #def check_password(self, password: str) -> bool:
        #"""Verify the user's password."""
        #return pwd_context.verify(password, self.password)

    def __repr__(self):
        """String representation of the User object."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

# Student Profile Model
class StudentProfile(Base):
    """Student profile with normalized subject relationships."""
    __tablename__ = 'student_profiles'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    grade_level = Column(String(20), nullable=False)
    availability = Column(String(255), nullable=False)
    bio = Column(Text)

    # Replace comma-separated subjects with many-to-many relationship
    subjects = relationship("Subject", secondary=student_subjects, backref="students")

    # Relationships
    user = relationship("User", back_populates="student_profile", lazy='joined')

    @property
    def uuid(self) -> str:
        return str(self.id)

    def __repr__(self):
        """String representation of the StudentProfile object."""
        return f"<StudentProfile(id={self.id}, user_id={self.user_id}, grade_level={self.grade_level})>"

# Tutor Profile Model
class TutorProfile(Base):
    """Tutor profile with expertise and rating system."""
    __tablename__ = 'tutor_profiles'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    hourly_rate = Column(Float, nullable=False)
    availability = Column(String(255), nullable=False)
    bio = Column(Text, nullable=False)
    rating = Column(Float)
    total_reviews = Column(Integer, default=0, nullable=False)

    # Table-level constraints
    __table_args__ = (
        CheckConstraint('hourly_rate >= 0', name='check_hourly_rate_positive'),
        CheckConstraint('rating >= 0 AND rating <= 5', name='check_rating_range'),
    )

    # Replace comma-separated expertise with many-to-many relationship
    expertise = relationship("Subject", secondary=tutor_expertise, backref="tutors")

    # Relationships
    user = relationship("User", back_populates="tutor_profile", lazy='joined')

    @property
    def uuid(self) -> str:
        return str(self.id)

    def __repr__(self):
        """String representation of the TutorProfile object."""
        return f"<TutorProfile(id={self.id}, user_id={self.user_id}, expertise={self.expertise})>"

# Chat Model
class Chat(Base):
    __tablename__ = 'chats'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tutor_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relationships
    student = relationship(
        "User",
        back_populates="chats_as_student",
        foreign_keys=[student_id],
        lazy='joined'
    )
    tutor = relationship(
        "User",
        back_populates="chats_as_tutor",
        foreign_keys=[tutor_id],
        lazy='joined'
    )
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        """String representation of the Chat object."""
        return f"<Chat(id={self.id}, student_id={self.student_id}, tutor_id={self.tutor_id})>"

# Message Model
class Message(Base):
    __tablename__ = 'messages'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    chat_id = Column(String(36), ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    sender_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    #reports = relationship("MessageReport", back_populates="message")

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship(
        "User",
        back_populates="messages_sent",
        foreign_keys=[sender_id],
        lazy='joined'
    )

    def __repr__(self):
        """String representation of the Message object."""
        return f"<Message(id={self.id}, chat_id={self.chat_id}, sender_id={self.sender_id})>"

# Appointment Model
class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tutor_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    topic = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False)
    duration = Column(Integer, default=60, nullable=False) # Duration in minutes
    status = Column(String, default="pending", nullable=False)  # 'pending', 'scheduled', 'completed', 'cancelled'
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False) # User who created the appointment

    # Relationships
    student = relationship("User", foreign_keys=[student_id], lazy='joined')
    tutor = relationship("User", foreign_keys=[tutor_id], lazy='joined')

    def __repr__(self):
        """String representation of the Appointment object."""
        return f"<Appointment(id={self.id}, student_id={self.student_id}, tutor_id={self.tutor_id}, topic={self.topic})>"

class MessageReport(Base):
    __tablename__ = 'message_reports'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey('messages.id'), nullable=False)
    reason = Column(Text, nullable=False)
    by = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    message = relationship("Message", backref="reports", foreign_keys=[message_id])

    def __repr__(self):
        """String representation of the MessageReport object."""
        return f"<MessageReport(id={self.id}, message_id={self.message_id}, reason={self.reason})>"

class UserReport(Base):
    __tablename__ = 'user_reports'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    reason = Column(Text, nullable=False)
    by = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    user = relationship("User", backref="reports", foreign_keys=[user_id])
    reported_by = relationship("User", foreign_keys=[by])

    def __repr__(self):
        """String representation of the UserReport object."""
        return f"<UserReport(id={self.id}, user_id={self.user_id}, reason={self.reason})>"

# Add indexes for frequently queried columns
Index('idx_user_email_role', User.email, User.role)
Index('idx_tutor_rating', TutorProfile.rating)
Index('idx_appointment_date', Appointment.date)
Index('idx_message_timestamp', Message.timestamp)

# Database setup
DATABASE_URL = get_settings().db_url
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Dependency to get DB session
def get_db():
    """Provides a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()