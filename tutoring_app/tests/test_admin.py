import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app 
from app.database.database import Base, get_db
from app.routers.authentication import create_user_in_db, generate_admin_token
from app.auth_tools import create_access_token, UserRole

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


def test_get_users(test_db):
    # Generate a valid access token for the admin user using generate_admin_token
    access_token = generate_admin_token(test_db)

    # Send a GET request to the get_users endpoint

    # Assert the response status code and content
    assert response.status_code == 200
    users = response.json()
    response = client.get("/admin/users", headers={"Authorization": f"Bearer {access_token}"})
    assert len(users) == 1
    assert users[0]["role"] == UserRole.ADMIN
