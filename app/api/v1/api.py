from fastapi import APIRouter
import logging

from app.api.v1.endpoints import auth
try:
    from app.api.v1.endpoints import users
except Exception as e:
    logging.getLogger(__name__).error(f"[IMPORT ERROR] app.api.v1.endpoints.users: {e}")

logging.debug(f"locals: {locals()}")
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
if 'users' in locals():
    api_router.include_router(users.router, prefix="/users", tags=["users"]) 