from fastapi import APIRouter

import logging

logging.debug("||| app/api/v1/api.py is imported (or reimported) |||")

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"]) 