from datetime import datetime
from user_profile import User

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

