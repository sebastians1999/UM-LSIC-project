import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app 
from app.database.database import Base, get_db
from app.routers.authentication import create_user_in_db, generate_admin_token

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

#now i want to make test that uses generate_admin_token to automatically create an admin user in the test database
#and then use the token to access the admin-only endpoint /admin/users and get a list of all users and verify that there is onely 1 user
def test_admin_user_access(test_db):
    # Generate an admin token, this also automatically creates an admin user in the test database
    admin_token = generate_admin_token(test_db)
    
    # Access the admin-only endpoint
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["username"] == "admin"

