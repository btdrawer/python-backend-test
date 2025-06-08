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

def test_read_users(test_user_client: TestClient, test_user: User, db: Session) -> None:
    verify_test_user(db, test_user)
    with override_get_db(db):
        response = test_user_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "testuser"
        assert data[0]["email"] == "test@example.com"
        assert "password" not in data[0]
        assert "hashed_password" not in data[0]

def test_read_users_unauthorized(client: TestClient, db: Session) -> None:
    response = client.get("/api/v1/users")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_read_user_me(test_user_client: TestClient, test_user: User, db: Session) -> None:
    verify_test_user(db, test_user)
    with override_get_db(db):
        response = test_user_client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "password" not in data
        assert "hashed_password" not in data

def test_read_user_me_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_user_me(test_user_client: TestClient, test_user: User, db: Session) -> None:
    with override_get_db(db):
        response = test_user_client.put(
            "/api/v1/users/me",
            json={
                "username": "updateduser",
                "email": "updated@example.com",
                "password": "newpassword123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "updateduser"
        assert data["email"] == "updated@example.com"
        
        # Verify changes in database
        db.refresh(test_user)
        assert test_user.username == "updateduser"
        assert test_user.email == "updated@example.com"
        assert test_user.verify_password("newpassword123")

def test_update_user_me_partial(test_user_client: TestClient, test_user: User, db: Session) -> None:
    with override_get_db(db):
        response = test_user_client.put(
            "/api/v1/users/me",
            json={
                "username": "updateduser"
                # Only update username
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "updateduser"
        assert data["email"] == "test@example.com"  # Unchanged
        
        # Verify changes in database
        db.refresh(test_user)
        assert test_user.username == "updateduser"
        assert test_user.email == "test@example.com"
        assert test_user.verify_password("testpassword123")  # Unchanged

def test_update_user_me_duplicate_username(
    test_user_client: TestClient, test_user: User, db: Session
) -> None:
    with override_get_db(db):
        # Create another user
        other_user = User(
            username="otheruser",
            email="other@example.com",
            is_active=True
        )
        other_user.set_password("password123")
        db.add(other_user)
        db.commit()
        
        # Try to update to existing username
        response = test_user_client.put(
            "/api/v1/users/me",
            json={
                "username": "otheruser"  # Already exists
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username already exists" in response.json()["detail"].lower()

def test_read_user_by_id(test_user_client: TestClient, test_user: User, db: Session) -> None:
    with override_get_db(db):
        response = test_user_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "password" not in data
        assert "hashed_password" not in data

def test_read_nonexistent_user(test_user_client: TestClient, db: Session) -> None:
    with override_get_db(db):
        response = test_user_client.get("/api/v1/users/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_user(test_user_client: TestClient, test_user: User, db: Session) -> None:
    with override_get_db(db):
        response = test_user_client.delete(f"/api/v1/users/{test_user.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        
        # Verify user was deleted from database
        user = db.query(User).filter(User.id == test_user.id).first()
        assert user is None

def test_delete_nonexistent_user(test_user_client: TestClient, db: Session) -> None:
    with override_get_db(db):
        response = test_user_client.delete("/api/v1/users/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND 