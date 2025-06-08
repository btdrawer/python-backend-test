import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import logging

from app.models.user import User
from app.main import app
from app.api import deps

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_register_user(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify user was created in database
    user = db.query(User).filter(User.username == "newuser").first()
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.verify_password("newpassword123")

def test_register_existing_username(client: TestClient, db: Session, test_user: User) -> None:
    logger.debug("Starting test_register_existing_username")
    try:
        # First verify the test user exists
        logger.debug("Verifying test user exists")
        existing_user = db.query(User).filter(User.username == "testuser").first()
        assert existing_user is not None, "Test user should exist in database"
        assert existing_user.id == test_user.id, "Should be the same user created by fixture"

        # Now try to register with the same username
        logger.debug("Attempting to register with existing username")
        
        # Override the get_db dependency to use our test session
        def override_get_db():
            try:
                yield db
            finally:
                pass  # Don't close the session, it's managed by the fixture
        
        app.dependency_overrides[deps.get_db] = override_get_db
        
        try:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",  # Already exists
                    "email": "different@example.com",
                    "password": "password123"
                }
            )
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text}")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "username already exists" in response.json()["detail"].lower()
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        logger.debug("test_register_existing_username completed successfully")
    except Exception as e:
        logger.error(f"Error in test_register_existing_username: {str(e)}")
        raise

def test_register_existing_email(client: TestClient, db: Session, test_user: User) -> None:
    logger.debug("Starting test_register_existing_email")
    try:
        # First verify the test user exists
        logger.debug("Verifying test user exists")
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        logger.debug(f"Existing user: {existing_user}")
        assert existing_user is not None, "Test user should exist in database"
        assert existing_user.id == test_user.id, "Should be the same user created by fixture"
        
        # Now try to register with the same email
        logger.debug("Attempting to register with existing email")
        
        # Override the get_db dependency to use our test session
        def override_get_db():
            try:
                yield db
            finally:
                pass  # Don't close the session, it's managed by the fixture
        
        app.dependency_overrides[deps.get_db] = override_get_db
        
        try:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "different",
                    "email": "test@example.com",  # Already exists
                    "password": "password123"
                }
            )
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text}")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "email already exists" in response.json()["detail"].lower()
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        logger.debug("test_register_existing_email completed successfully")
    except Exception as e:
        logger.error(f"Error in test_register_existing_email: {str(e)}")
        raise

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

def test_login_success(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "incorrect username or password" in response.json()["detail"].lower()

def test_login_nonexistent_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent",
            "password": "password123"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "incorrect username or password" in response.json()["detail"].lower()

def test_login_inactive_user(client: TestClient, db: Session, test_user: User) -> None:
    # Deactivate the test user
    test_user.is_active = False
    db.commit()
    
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "inactive user" in response.json()["detail"].lower() 