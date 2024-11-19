from datetime import datetime
from typing import List, Optional, Union
from user_profile import User


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
