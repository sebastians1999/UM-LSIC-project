# mock_data.py

from datetime import datetime, timedelta

mock_users = [
    {"id": 1, "email": "admin@example.com", "password": "hashed_password", "role": "admin", "name": "Admin"},
    {"id": 2, "email": "student@example.com", "password": "hashed_password", "role": "student", "name": "Student"},
    {"id": 3, "email": "tutor@example.com", "password": "hashed_password", "role": "tutor", "name": "Tutor"},
]

mock_chats = [
    {"id": 1, "student_id": 2, "tutor_id": 3, "created_at": datetime.now(), "updated_at": datetime.now()},
]

mock_messages = [
    {"id": 1, "chat_id": 1, "sender_id": 2, "content": "Hello", "timestamp": datetime.now()},
]

mock_appointments = [
    {"id": 1, "student_id": 2, "tutor_id": 3, "topic": "Math Tutoring", "date": datetime.now() + timedelta(days=1), "status": "scheduled"},
]

mock_reports = [
    {"id": 1, "message_id": 1, "reported_by": 2, "reason": "Inappropriate content", "timestamp": datetime.now()},
]

mock_tutors = [
    {"id": 3, "user_id": 3, "expertise": "Math, Science", "hourly_rate": 30.0, "availability": "Weekends", "bio": "Experienced tutor", "rating": 4.5, "total_reviews": 10},
]

mock_users.extend(mock_tutors)