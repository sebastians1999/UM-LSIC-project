from datetime import datetime
from typing import List, Optional, Union



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