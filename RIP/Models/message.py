from datetime import datetime
from typing import List, Optional, Union
from user_profile import User
from chat import Chat


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
