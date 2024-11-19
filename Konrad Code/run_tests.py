import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def call_endpoint(method, url, **kwargs):
    try:
        response = method(url, **kwargs)
        print(f"URL: {url}")
        print(f"Method: {method.__name__.upper()}")
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            print("Response: No JSON response")
        print("-" * 50)
        return response
    except requests.RequestException as e:
        print(f"Error calling {url}: {e}")
        print("-" * 50)
        return None

def setup_test_data(base_url):
    """Create necessary test data before running tests"""
    # Create admin
    call_endpoint(requests.post, f"{base_url}/admin/initialize")
    
    # Create student
    student_response = call_endpoint(
        requests.post, 
        f"{base_url}/users/register",
        params={
            "email": "student@example.com",
            "password": "password123",
            "role": "student",
            "name": "Test Student"
        }
    )
    
    # Create tutor
    tutor_response = call_endpoint(
        requests.post,
        f"{base_url}/users/register",
        params={
            "email": "tutor@example.com",
            "password": "password123",
            "role": "tutor",
            "name": "Test Tutor"
        }
    )
    
    # Create chat between student and tutor
    chat_response = call_endpoint(
        requests.post,
        f"{base_url}/student/chat",
        params={
            "student_id": 2,  # Assuming student ID is 2
            "tutor_id": 3     # Assuming tutor ID is 3
        }
    )

def run_all_tests():
    # Setup test data first
    setup_test_data(BASE_URL)
    
    # Initialize Admin
    call_endpoint(requests.post, f"{BASE_URL}/admin/initialize")

    # Admin Login
    call_endpoint(requests.post, f"{BASE_URL}/admin/login", params={"email": "admin@example.com", "password": "hashed_password"})

    # Admin Dashboard
    call_endpoint(requests.get, f"{BASE_URL}/admin/dashboard")

    # Get Chat Messages
    call_endpoint(requests.get, f"{BASE_URL}/admin/chats/1/messages")

    # Delete Chat Message
    call_endpoint(requests.delete, f"{BASE_URL}/admin/chats/1/messages/1")

    # Send Chat Message
    call_endpoint(requests.post, f"{BASE_URL}/admin/chats/1/messages", params={"content": "Admin message"})

    # Get Reports
    call_endpoint(requests.get, f"{BASE_URL}/admin/reports")

    # Get Report
    call_endpoint(requests.get, f"{BASE_URL}/admin/reports/1")

    # Ban User
    call_endpoint(requests.post, f"{BASE_URL}/admin/users/2/ban", params={"ban_until": (datetime.now() + timedelta(days=1)).isoformat()})

    # Get Tutors
    call_endpoint(requests.get, f"{BASE_URL}/student/tutors")

    # Create Chat
    call_endpoint(requests.post, f"{BASE_URL}/student/chat", params={"student_id": 2, "tutor_id": 3})

    # Create Tutor
    call_endpoint(requests.post, f"{BASE_URL}/tutor/create", params={"user_id": 3, "expertise": "Math, Science", "hourly_rate": 30.0, "availability": "Weekends", "bio": "Experienced tutor"})

    # Verify Tutor Creation
    call_endpoint(requests.get, f"{BASE_URL}/tutor/availability/3")

    # Update Availability
    call_endpoint(requests.patch, f"{BASE_URL}/tutor/availability", params={"tutor_id": 3, "availability": "Weekends"})

    # Register User
    call_endpoint(requests.post, f"{BASE_URL}/users/register", params={"email": "uniqueuser@example.com", "password": "hashed_password", "role": "student", "name": "Unique User"})

    # Update Profile
    call_endpoint(requests.put, f"{BASE_URL}/users/profile", params={"user_id": 2, "bio": "Updated bio"})

    # Get User
    call_endpoint(requests.get, f"{BASE_URL}/users/2")

    # Get Chats
    call_endpoint(requests.get, f"{BASE_URL}/chats", params={"user_id": 2})

    # Get Chat
    call_endpoint(requests.get, f"{BASE_URL}/chats/1")

    # Send Message
    call_endpoint(requests.post, f"{BASE_URL}/chats/1/messages", params={"sender_id": 2, "content": "New message"})

    # Report Message
    call_endpoint(requests.post, f"{BASE_URL}/reports/messages/1/1")

    # Get Appointments
    call_endpoint(requests.get, f"{BASE_URL}/users/2/appointments")

    # Schedule Meeting
    call_endpoint(requests.post, f"{BASE_URL}/meetings", params={"student_id": 2, "tutor_id": 3, "topic": "Science Tutoring", "date": (datetime.now() + timedelta(days=2)).isoformat()})

    # Get Current Meetings
    call_endpoint(requests.get, f"{BASE_URL}/meetings", params={"user_id": 2, "current": True})

    # Get Meeting
    call_endpoint(requests.get, f"{BASE_URL}/meetings/1")

    # Update Meeting
    call_endpoint(requests.patch, f"{BASE_URL}/meetings/1", params={"topic": "Updated topic"})

    # Cancel Meeting
    call_endpoint(requests.delete, f"{BASE_URL}/meetings/1")

    # Submit Rating
    call_endpoint(requests.post, f"{BASE_URL}/ratings", params={"user_id": 3, "rating": 5.0, "review": "Great tutor"})

    # Contact Support
    call_endpoint(requests.post, f"{BASE_URL}/support/contact", params={"user_id": 2, "message": "Need help"})

    # Delete User
    call_endpoint(requests.delete, f"{BASE_URL}/users/2")

    # Get Tutor Availability
    call_endpoint(requests.get, f"{BASE_URL}/tutor/availability/3")

    # Get Tutor Details
    call_endpoint(requests.get, f"{BASE_URL}/student/tutors/3")

    # Get All Users
    call_endpoint(requests.get, f"{BASE_URL}/users")

if __name__ == "__main__":
    run_all_tests()