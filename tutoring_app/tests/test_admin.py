import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app #how do i correctly call the app
from app.database.database import Base, get_db #how do i correctly call the database
from app.routers import user #how do i create mock users correctly
from app.auth_tools import create_access_token, UserRole
from app.schemas import UserCreate

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create the test client
client = TestClient(app)

# Create the test database tables
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="module")
def test_db():
    # Create a new database session for the test
    db = TestingSessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="module")
def admin_user(test_db):
    # Manually insert an admin user into the database
    admin = user(
        email="admin@example.com",
        hashed_password="hashedpassword",  # This should be a hashed password
        role=UserRole.ADMIN
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin

def test_create_user(test_db, admin_user):
    # Generate a valid access token for the admin user
    access_token = create_access_token(data={"sub": admin_user.id, "role": UserRole.ADMIN})

    # Define the new user data
    new_user_data = {
        "email": "newuser@example.com",
        "password": "password123",
        "name": "New User",
        "role": "student"
    }

    # Send a POST request to the create_user endpoint
    response = client.post(
        "/users/create",
        json=new_user_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    # Assert the response status code and content
    assert response.status_code == 200
    assert response.json()["message"] == "User created successfully"
    assert "user_id" in response.json()

    # Verify the user was added to the database
    db_user = test_db.query(User).filter(User.email == new_user_data["email"]).first()
    assert db_user is not None
    assert db_user.email == new_user_data["email"]
    assert db_user.name == new_user_data["name"]
    assert db_user.role == new_user_data["role"]