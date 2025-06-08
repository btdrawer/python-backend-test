from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from cryptography.fernet import Fernet
import logging
from app.core.config import settings
from app.db.session import Base

logger = logging.getLogger(__name__)

# Generate a key for AES encryption if not exists
if not hasattr(settings, 'ENCRYPTION_KEY'):
    settings.ENCRYPTION_KEY = Fernet.generate_key()

fernet = Fernet(settings.ENCRYPTION_KEY)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # AES-256 encrypted
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def set_password(self, password: str) -> None:
        """Encrypt and set the user's password"""
        encrypted_password = fernet.encrypt(password.encode())
        self.hashed_password = encrypted_password.decode()

    def verify_password(self, password: str) -> bool:
        """Verify the user's password"""
        try:
            logger.debug(f"Attempting to verify password for user: {self.username}")
            decrypted_password = fernet.decrypt(self.hashed_password.encode())
            is_valid = decrypted_password.decode() == password
            logger.debug(f"Password verification {'successful' if is_valid else 'failed'} for user: {self.username}")
            return is_valid
        except Exception as e:
            logger.error(f"Error verifying password for user {self.username}: {str(e)}")
            return False 