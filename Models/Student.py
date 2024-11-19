from datetime import datetime
from typing import List, Optional, Union


# Base User Class
class User:
    def __init__(
        self,
        user_id: int,
        role: str,
        email: str,
        password: str,
        name: str,
        is_banned_until: Optional[datetime] = None,
    ):
        self.id = user_id
        self.role = role  # 'admin', 'student', 'tutor'
        self.email = email
        self.password = password
        self.name = name
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_banned_until = is_banned_until  # None means not banned

    def _repr_(self):
        return f"User(id={self.id}, role={self.role}, email={self.email}, name={self.name}, is_banned_until={self.is_banned_until})"


# Student Profile Class
class StudentProfile:
    def __init__(
        self,
        user: User,
        grade_level: str,
        subjects: List[str],
        availability: str,
        bio: Optional[str] = None,
    ):
        self.user = user
        self.grade_level = grade_level
        self.subjects = subjects  # List of subjects the student is interested in
        self.availability = availability  # Preferred availability
        self.bio = bio

    def _repr_(self):
        return f"StudentProfile(user={self.user}, grade_level={self.grade_level}, subjects={self.subjects}, availability={self.availability}, bio={self.bio})"


# Tutor Profile Class
class TutorProfile:
    def __init__(
        self,
        user: User,
        expertise: List[str],
        hourly_rate: float,
        availability: str,
        bio: str,
        rating: Optional[float] = None,
        total_reviews: int = 0,
    ):
        self.user = user
        self.expertise = expertise  # List of subjects the tutor is an expert in
        self.hourly_rate = hourly_rate
        self.availability = availability  # Tutor's availability
        self.bio = bio
        self.rating = rating  # Average rating
        self.total_reviews = total_reviews

    def _repr_(self):
        return f"TutorProfile(user={self.user}, expertise={self.expertise}, hourly_rate={self.hourly_rate}, availability={self.availability}, rating={self.rating}, total_reviews={self.total_reviews})"


# Chat Class
class Chat:
    def __init__(self, chat_id: int, student: User, tutor: User):
        self.id = chat_id
        self.student = student
        self.tutor = tutor
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def _repr_(self):
        return f"Chat(id={self.id}, student={self.student}, tutor={self.tutor})"


# Message Class
class Message:
    def __init__(self, message_id: int, chat: Chat, sender: User, content: str):
        self.id = message_id
        self.chat = chat
        self.sender = sender
        self.content = content
        self.timestamp = datetime.now()
        self.is_deleted = False

    def _repr_(self):
        return f"Message(id={self.id}, sender={self.sender}, content={self.content}, is_deleted={self.is_deleted})"


# Appointment Class
class Appointment:
    def __init__(
        self,
        appointment_id: int,
        student: User,
        tutor: User,
        topic: str,
        date: datetime,
        status: str = "scheduled",
    ):
        self.id = appointment_id
        self.student = student
        self.tutor = tutor
        self.topic = topic
        self.date = date
        self.status = status  # 'scheduled', 'completed', 'cancelled'

    def _repr_(self):
        return f"Appointment(id={self.id}, student={self.student}, tutor={self.tutor}, topic={self.topic}, date={self.date}, status={self.status})"


# Example Usage
if __name__ == "__main__":
    # Create Users
    student_user = User(
        1, "student", "student@example.com", "hashed_password", "John Doe"
    )
    tutor_user = User(
        2,
        "tutor",
        "tutor@example.com",
        "hashed_password",
        "Jane Smith",
        is_banned_until=None,
    )

    # Create Profiles
    student_profile = StudentProfile(
        student_user,
        "Undergraduate",
        ["Math", "Physics"],
        "Mon-Fri 9AM-5PM",
        "Passionate learner",
    )
    tutor_profile = TutorProfile(
        tutor_user,
        ["Math", "Physics"],
        25.0,
        "Mon-Fri 1PM-5PM",
        "Experienced tutor",
        rating=4.8,
        total_reviews=10,
    )

    # Create Chat and Messages
    chat = Chat(1, student_user, tutor_user)
    message = Message(1, chat, student_user, "Hello, I need help with physics.")

    # Create Appointment
    appointment = Appointment(
        1, student_user, tutor_user, "Physics Tutoring", datetime(2024, 11, 20, 10, 0)
    )

    # Print Objects
    print(student_user)
    print(tutor_user)
    print(student_profile)
    print(tutor_profile)
    print(chat)
    print(message)
    print(appointment)
