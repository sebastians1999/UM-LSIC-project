from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime

# Base class for ORM models
Base = declarative_base()

# User Model
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    role = Column(String, nullable=False)  # 'admin', 'student', 'tutor'
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    is_banned_until = Column(DateTime, nullable=True)

    # Relationships
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    tutor_profile = relationship("TutorProfile", back_populates="user", uselist=False)
    chats_as_student = relationship("Chat", back_populates="student", foreign_keys='Chat.student_id')
    chats_as_tutor = relationship("Chat", back_populates="tutor", foreign_keys='Chat.tutor_id')

class StudentProfile(Base):
    __tablename__ = 'student_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    grade_level = Column(String, nullable=False)
    subjects = Column(Text, nullable=False)  # Comma-separated list of subjects
    availability = Column(String, nullable=False)
    bio = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="student_profile")

class TutorProfile(Base):
    __tablename__ = 'tutor_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    expertise = Column(Text, nullable=False)  # Comma-separated list of subjects
    hourly_rate = Column(Float, nullable=False)
    availability = Column(String, nullable=False)
    bio = Column(Text, nullable=False)
    rating = Column(Float, nullable=True)
    total_reviews = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="tutor_profile")

class Chat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tutor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relationships
    student = relationship("User", back_populates="chats_as_student", foreign_keys=[student_id])
    tutor = relationship("User", back_populates="chats_as_tutor", foreign_keys=[tutor_id])
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tutor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    topic = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled", nullable=False)  # 'scheduled', 'completed', 'cancelled'

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    tutor = relationship("User", foreign_keys=[tutor_id])

# Database setup
DATABASE_URL = "sqlite:///tutoring_platform.db"
engine = create_engine(DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
