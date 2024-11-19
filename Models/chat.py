from datetime import datetime
from typing import List, Optional, Union
from user_profile import User


class Chat:
    def __init__(self, chat_id: int, student: User, tutor: User):
        self.id = chat_id
        self.student = student
        self.tutor = tutor
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def _repr_(self):
        return f"Chat(id={self.id}, student={self.student}, tutor={self.tutor})"
