from datetime import datetime
from Models.user_profile import User
from Models.student_profile import StudentProfile
from Models.tutor_profile import TutorProfile
from Models.chat import Chat
from Models.message import Message
from Models.appointment import Appointment




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
