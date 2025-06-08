import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User

def test_read_users(test_user_client: TestClient, test_user: User) -> None:
    response = test_user_client.get("/api/v1/users/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["username"] == "testuser"
    assert data[0]["email"] == "test@example.com"
    assert "password" not in data[0]
    assert "hashed_password" not in data[0]

def test_read_users_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/users/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_read_user_me(test_user_client: TestClient, test_user: User) -> None:
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

def test_read_user_by_id(test_user_client: TestClient, test_user: User) -> None:
    response = test_user_client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "password" not in data
    assert "hashed_password" not in data

def test_read_nonexistent_user(test_user_client: TestClient) -> None:
    response = test_user_client.get("/api/v1/users/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_user(test_user_client: TestClient, test_user: User, db: Session) -> None:
    response = test_user_client.delete(f"/api/v1/users/{test_user.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    
    # Verify user was deleted from database
    user = db.query(User).filter(User.id == test_user.id).first()
    assert user is None

def test_delete_nonexistent_user(test_user_client: TestClient) -> None:
    response = test_user_client.delete("/api/v1/users/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND 