import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import logging
from contextlib import contextmanager
from typing import Generator, Callable

from app.models.user import User
from app.main import app
from app.api import deps

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@contextmanager
def override_get_db(db: Session) -> Generator[None, None, None]:
    """Context manager to override the get_db dependency with a test session"""
    def _override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[deps.get_db] = _override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.clear()

def verify_test_user(db: Session, test_user: User) -> None:
    """Verify that the test user exists in the database and matches the fixture"""
    logger.debug("Verifying test user exists in database")
    db_user = db.query(User).filter(User.username == "testuser").first()
    assert db_user is not None, "Test user should exist in database"
    assert db_user.id == test_user.id, "Should be the same user created by fixture"
    return db_user

def test_register_user(client: TestClient, db: Session) -> None:
    """Test user registration"""
    logger.debug("Starting test_register_user")
    
    with override_get_db(db):
        logger.debug("Attempting to register new user")
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpassword123"
            }
        )
        logger.debug(f"Register response status: {response.status_code}")
        logger.debug(f"Register response body: {response.text}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data
        assert "hashed_password" not in data

        # Verify user was created in database
        logger.debug("Verifying user in database")
        user = db.query(User).filter(User.username == "newuser").first()
        assert user is not None, "User should exist in database"
        assert user.email == "newuser@example.com"
        assert user.verify_password("newpassword123")
        logger.debug("test_register_user completed successfully")

def test_register_existing_username(client: TestClient, db: Session, test_user: User) -> None:
    """Test registration with existing username"""
    logger.debug("Starting test_register_existing_username")
    
    # First verify the test user exists
    verify_test_user(db, test_user)

    with override_get_db(db):
        logger.debug("Attempting to register with existing username")
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",  # Already exists
                "email": "different@example.com",
                "password": "password123"
            }
        )
        logger.debug(f"Register response status: {response.status_code}")
        logger.debug(f"Register response body: {response.text}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username already exists" in response.json()["detail"].lower()
        logger.debug("test_register_existing_username completed successfully")

def test_register_existing_email(client: TestClient, db: Session, test_user: User) -> None:
    """Test registration with existing email"""
    logger.debug("Starting test_register_existing_email")
    
    # First verify the test user exists
    verify_test_user(db, test_user)

    with override_get_db(db):
        logger.debug("Attempting to register with existing email")
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "different",
                "email": "test@example.com",  # Already exists
                "password": "password123"
            }
        )
        logger.debug(f"Register response status: {response.status_code}")
        logger.debug(f"Register response body: {response.text}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email already exists" in response.json()["detail"].lower()
        logger.debug("test_register_existing_email completed successfully")

def test_register_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "invalid-email",
            "password": "password123"
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_register_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "short"  # Too short
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_login_success(client: TestClient, db: Session, test_user: User) -> None:
    """Test successful login with test user"""
    logger.debug("Starting test_login_success")
    
    # Verify test user exists in database
    verify_test_user(db, test_user)
    
    with override_get_db(db):
        logger.debug("Attempting login")
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123"
            }
        )
        logger.debug(f"Login response status: {response.status_code}")
        logger.debug(f"Login response body: {response.text}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        logger.debug("test_login_success completed successfully")

def test_login_wrong_password(client: TestClient, db: Session, test_user: User) -> None:
    """Test login with incorrect password"""
    logger.debug("Starting test_login_wrong_password")
    
    # Verify test user exists
    verify_test_user(db, test_user)

    with override_get_db(db):
        logger.debug("Attempting login with wrong password")
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        logger.debug(f"Login response status: {response.status_code}")
        logger.debug(f"Login response body: {response.text}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect username or password" in response.json()["detail"].lower()
        logger.debug("test_login_wrong_password completed successfully")

def test_login_nonexistent_user(client: TestClient, db: Session) -> None:
    """Test login with non-existent user"""
    logger.debug("Starting test_login_nonexistent_user")
    
    with override_get_db(db):
        logger.debug("Attempting login with non-existent user")
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        logger.debug(f"Login response status: {response.status_code}")
        logger.debug(f"Login response body: {response.text}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect username or password" in response.json()["detail"].lower()
        logger.debug("test_login_nonexistent_user completed successfully")

def test_login_inactive_user(client: TestClient, db: Session, test_user: User) -> None:
    """Test login with inactive user"""
    logger.debug("Starting test_login_inactive_user")
    
    # Verify test user exists and is active
    db_user = verify_test_user(db, test_user)
    assert db_user.is_active, "Test user should be active initially"
    
    # Deactivate the test user
    logger.debug("Deactivating test user")
    db_user.is_active = False
    db.commit()
    db.refresh(db_user)
    assert not db_user.is_active, "Test user should be inactive after update"

    with override_get_db(db):
        logger.debug("Attempting login with inactive user")
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123"
            }
        )
        logger.debug(f"Login response status: {response.status_code}")
        logger.debug(f"Login response body: {response.text}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inactive user" in response.json()["detail"].lower()
        logger.debug("test_login_inactive_user completed successfully") 