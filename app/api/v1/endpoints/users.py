import logging
logging.getLogger(__name__).debug("[IMPORT] app.api.v1.endpoints.users imported")
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.crud import user as crud_user
from app.schemas.user import User, UserCreate, UserUpdate

router = APIRouter()

@router.get("", response_model=List[User])
@router.get("/", response_model=List[User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> List[User]:
    """
    Retrieve users.
    """
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users

@router.post("", response_model=User)
@router.post("/", response_model=User)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_user),
) -> User:
    """
    Create new user.
    """
    user = crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    user = crud_user.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system.",
        )
    user = crud_user.create_user(db, user_in)
    return user

@router.get("/me", response_model=User)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> User:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=User)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> User:
    """
    Update own user.
    """
    user = crud_user.update_user(db, user_id=current_user.id, user=user_in)
    return user

@router.get("/{user_id}", response_model=User)
def read_user_by_id(
    user_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> User:
    """
    Get a specific user by id.
    """
    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user

@router.delete("/{user_id}", response_model=User)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> User:
    """
    Delete a user.
    """
    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user = crud_user.delete_user(db, user_id=user_id)
    return user 