from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime
import logging
import uvicorn
import unittest
import os
from database import (
    Base, engine, SessionLocal, User, Chat, Message, 
    Appointment, StudentProfile, TutorProfile, get_db
)

# Pydantic models for validation
class AdminCredentials(BaseModel):
    email: str
    password: str

class BanRequest(BaseModel):
    ban_until: datetime

class TestAdminController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use test database
        cls.test_db_url = "sqlite:///test_tutoring_platform.db"
        cls.engine = create_engine(cls.test_db_url)
        cls.TestSessionLocal = sessionmaker(bind=cls.engine)
        
        # Create test client
        cls.client = TestClient(app)
        
        # Override get_db dependency
        def override_get_db():
            db = cls.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        # Reset database
        Base.metadata.drop_all(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)
        
        # Initialize test data
        cls.init_test_data()

    @classmethod
    def init_test_data(cls):
        db = cls.TestSessionLocal()
        
        # Create admin
        admin = User(
            role="admin",
            email="admin@test.com",
            password="testpass",
            name="Test Admin"
        )
        
        # Create student with profile
        student = User(
            role="student",
            email="student@test.com",
            password="testpass",
            name="Test Student"
        )
        student_profile = StudentProfile(
            user=student,
            grade_level="12",
            subjects="Math,Physics",
            availability="Weekdays"
        )
        
        # Create tutor with profile
        tutor = User(
            role="tutor",
            email="tutor@test.com",
            password="testpass",
            name="Test Tutor"
        )
        tutor_profile = TutorProfile(
            user=tutor,
            expertise="Mathematics,Physics",
            hourly_rate=50.0,
            availability="Weekdays",
            bio="Test tutor"
        )
        
        db.add_all([admin, student, tutor])
        db.commit()
        
        # Create chat and messages
        chat = Chat(student_id=student.id, tutor_id=tutor.id)
        db.add(chat)
        db.commit()
        
        messages = [
            Message(chat_id=chat.id, sender_id=student.id, content="Test message 1"),
            Message(chat_id=chat.id, sender_id=tutor.id, content="Test message 2")
        ]
        db.add_all(messages)
        
        # Create appointment
        appointment = Appointment(
            student_id=student.id,
            tutor_id=tutor.id,
            topic="Test Topic",
            date=datetime(2024, 12, 1, 14, 0),
            status="scheduled"
        )
        db.add(appointment)
        db.commit()
        db.close()

    def test_admin_initialize(self):
        """Test admin initialization endpoint"""
        response = self.client.post(
            "/admin/initialize",
            json={"email": "admin2@test.com", "password": "testpass"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Admin already exists", response.json()["detail"])

    def test_admin_login_success(self):
        """Test successful admin login"""
        response = self.client.post(
            "/admin/login",
            json={"email": "admin@test.com", "password": "testpass"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login successful", response.json()["message"])

    def test_admin_login_fail(self):
        """Test failed admin login"""
        response = self.client.post(
            "/admin/login",
            json={"email": "wrong@test.com", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, 401)

    def test_dashboard(self):
        """Test dashboard statistics"""
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["users"], 3)  # admin, student, tutor
        self.assertEqual(data["chats"], 1)
        self.assertEqual(data["messages"], 2)
        self.assertEqual(data["appointments"], 1)

    def test_chat_messages(self):
        """Test retrieving chat messages"""
        response = self.client.get("/admin/chats/1/messages")
        self.assertEqual(response.status_code, 200)
        messages = response.json()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "Test message 1")

    def test_ban_user(self):
        """Test banning a user"""
        response = self.client.post(
            "/admin/users/2/ban",  # Ban student user
            json={"ban_until": "2024-12-31T23:59:59"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("User banned", response.json()["message"])

    @classmethod
    def tearDownClass(cls):
        # Clean up test database
        Base.metadata.drop_all(bind=cls.engine)
        os.remove("test_tutoring_platform.db")