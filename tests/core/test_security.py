import pytest
from datetime import timedelta
from fastapi import HTTPException

from app.core import security
from app.core.config import settings

def test_create_access_token() -> None:
    user_id = 1
    token = security.create_access_token(user_id)
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_access_token_with_expires_delta() -> None:
    user_id = 1
    expires_delta = timedelta(minutes=30)
    token = security.create_access_token(user_id, expires_delta=expires_delta)
    assert isinstance(token, str)
    assert len(token) > 0

def test_verify_token() -> None:
    user_id = 1
    token = security.create_access_token(user_id)
    verified_id = security.verify_token(token)
    assert verified_id == user_id

def test_verify_token_invalid() -> None:
    with pytest.raises(HTTPException) as exc_info:
        security.verify_token("invalid_token")
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)

def test_verify_token_expired() -> None:
    user_id = 1
    # Create a token that expires immediately
    token = security.create_access_token(user_id, expires_delta=timedelta(microseconds=1))
    # Wait a moment to ensure token expires
    import time
    time.sleep(0.1)
    
    with pytest.raises(HTTPException) as exc_info:
        security.verify_token(token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail) 