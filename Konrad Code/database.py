from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, Enum, Index, CheckConstraint
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
import enum
from passlib.context import CryptContext

# Base class for ORM models
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Enum for user roles
class UserRole(enum.Enum):
    ADMIN = "admin"
    STUDENT = "student"
    TUTOR = "tutor"

# User Model
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    role = Column(Enum(UserRole), nullable=False)  # Use Enum for role
    email = Column(String, unique=True, nullable=False, index=True)  # Email should be unique and indexed
    password = Column(String, nullable=False)  # Store hashed passwords
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    is_banned_until = Column(DateTime, nullable=True)  # Nullable field for ban duration

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

    def set_password(self, password: str):
        """Hash and set the user's password."""
        self.password = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the user's password."""
        return pwd_context.verify(password, self.password)

    def __repr__(self):
        """String representation of the User object."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

# Student Profile Model
class StudentProfile(Base):
    __tablename__ = 'student_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    grade_level = Column(String, nullable=False)
    subjects = Column(Text, nullable=False)  # Comma-separated list of subjects
    availability = Column(String, nullable=False)
    bio = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="student_profile", lazy='joined')

    def __repr__(self):
        """String representation of the StudentProfile object."""
        return f"<StudentProfile(id={self.id}, user_id={self.user_id}, grade_level={self.grade_level})>"

# Tutor Profile Model
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
    user = relationship("User", back_populates="tutor_profile", lazy='joined')

    def __repr__(self):
        """String representation of the TutorProfile object."""
        return f"<TutorProfile(id={self.id}, user_id={self.user_id}, expertise={self.expertise})>"

# Chat Model
class Chat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tutor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
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
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

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
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tutor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    topic = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled", nullable=False)  # 'scheduled', 'completed', 'cancelled'

    # Relationships
    student = relationship("User", foreign_keys=[student_id], lazy='joined')
    tutor = relationship("User", foreign_keys=[tutor_id], lazy='joined')

    def __repr__(self):
        """String representation of the Appointment object."""
        return f"<Appointment(id={self.id}, student_id={self.student_id}, tutor_id={self.tutor_id}, topic={self.topic})>"

# Database setup
DATABASE_URL = "sqlite:///tutoring_platform.db"
engine = create_engine(DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Dependency to get DB session
def get_db():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()