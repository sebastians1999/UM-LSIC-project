import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app 
from database.database import Base, get_db, UserRole, User
from routers.authentication import create_user_in_db
#from models import UserRole # have to adjust this

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

def test_admin_user_access(test_db):
    # Generate a valid access token for the admin user using generate_admin_token
    admin_token = client.get('/auth/generate-admin-token').json()['access_token']
    print(admin_token)

    # Access the admin-only endpoint to get all users
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Verify the response
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["role"] == UserRole.ADMIN.name

def test_create_user(test_db):
    # Generate a valid access token for the admin user
    admin_token = client.get('/auth/generate-admin-token').json()['access_token']

    # Define the new user data
    new_user_data = {
        "name": "New User",
        "email": "newuser@example.com",
        "role": "student"
    }

    # Send a POST request to the create_user endpoint
    response = client.post(
        "/admin/users",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
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

def test_delete_user(test_db):
    # Generate a valid access token for the admin user
    admin_token = client.get('/auth/generate-admin-token').json()['access_token']

    # Create a user to be deleted
    user_to_delete = create_user_in_db(test_db, {
        "email": "deleteuser@example.com",
        "name": "Delete User",
        "role": UserRole.STUDENT
    })

    # Send a DELETE request to the delete_user endpoint
    response = client.delete(
        f"/admin/users/{user_to_delete.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Assert the response status code and content
    assert response.status_code == 200
    assert response.json()["message"] == f"User {user_to_delete.id} deleted"

    # Verify the user was deleted from the database
    db_user = test_db.query(User).filter(User.id == user_to_delete.id).first()
    assert db_user is None

def test_ban_user(test_db):
    # Generate a valid access token for the admin user
    admin_token = client.get('/auth/generate-admin-token').json()['access_token']

    # Create a user to be banned
    user_to_ban = create_user_in_db(test_db, {
        "email": "banuser@example.com",
        "name": "Ban User",
        "role": UserRole.STUDENT
    })

    # Send a POST request to the ban_user endpoint
    response = client.post(
        f"/admin/users/{user_to_ban.id}/ban",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Assert the response status code and content
    assert response.status_code == 200
    assert response.json()["message"] == f"User {user_to_ban.id} banned"

    # Verify the user was banned in the database
    db_user = test_db.query(User).filter(User.id == user_to_ban.id).first()
    assert db_user is not None
    assert db_user.is_banned is True
