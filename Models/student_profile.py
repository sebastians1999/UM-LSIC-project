from datetime import datetime
from typing import List, Optional, Union
from user_profile import User



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



