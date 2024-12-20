
# Tutoring Platform API

A FastAPI-based backend for a tutoring platform that connects students with tutors.

## Features

- User authentication via GitLab OAuth
- Role-based access control (Admin, Student, Tutor)
- Real-time chat functionality
- Appointment scheduling
- Profile management
- Rate limiting and security features

## Tech Stack

- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL/SQLite
- Argon2 password hashing
- OAuth2 authentication

## Setup Development Environment

1. Clone the repository.

2. Create a Python Environment
	
   python -m venv env

3. Activate the Environment

	-    On Windows: .\env\Scripts\activate
	-    On Mac: source env/bin/activate

4. Download the dependencies from the requirements.txt file

	pip install -r requirements.txt

5. Inside this environment, navigate to the app folder

6. Create an .env file to declare keys, follow the config.py file for more instructions. When the file is created, make sure it’s in the same directory as the main.py

7. Run main.py in the virtual environment
