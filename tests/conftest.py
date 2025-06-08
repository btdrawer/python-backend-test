import pytest
from typing import Generator, Dict
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import time
from sqlalchemy.exc import OperationalError
import uvicorn
import threading
import requests
from contextlib import contextmanager
import os
import logging

from app.main import app
from app.db.session import Base, get_db
from app.core.config import Settings, settings
from app.models.user import User
from app.core import security

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Override environment variables for testing
os.environ.update({
    "POSTGRES_SERVER": "127.0.0.1",
    "POSTGRES_PORT": "5433",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "POSTGRES_DB": "app_test",
    "ENCRYPTION_KEY": "test-key-123"  # Add a test encryption key
})

# Create new settings instance with test values
test_settings = Settings()
# Override the global settings
for key, value in test_settings.dict().items():
    setattr(settings, key, value)

def wait_for_db(max_retries=10, retry_interval=2):
    """Wait for database to become available and ready"""
    logger.debug("Starting wait_for_db")
    for i in range(max_retries):
        try:
            logger.debug(f"Attempt {i+1}/{max_retries} to connect to database")
            engine = create_engine(str(settings.DATABASE_URL))
            logger.debug("Engine created, attempting to connect")
            with engine.connect() as conn:
                logger.debug("Connected to database, executing test query")
                # Try to execute a simple query to verify database is ready
                conn.execute(text("SELECT 1"))
                logger.debug("Test query successful, creating tables")
                # Create all tables
                Base.metadata.create_all(bind=engine)
                logger.debug("Tables created successfully")
            return engine
        except OperationalError as e:
            logger.error(f"Database not ready, attempt {i+1}/{max_retries}: {str(e)}")
            if i == max_retries - 1:
                raise
            logger.debug(f"Waiting {retry_interval} seconds before next attempt")
            time.sleep(retry_interval)
    logger.debug("wait_for_db completed successfully")

def wait_for_server(max_retries=5, retry_interval=1):
    """Wait for server to become available"""
    logger.debug("Starting wait_for_server")
    for i in range(max_retries):
        try:
            logger.debug(f"Attempt {i+1}/{max_retries} to connect to server")
            response = requests.get("http://localhost:8000/api/v1/health")
            if response.status_code == 200:
                logger.debug("Server is available and healthy")
                return
            logger.debug(f"Server returned status code {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Server not ready, attempt {i+1}/{max_retries}: {str(e)}")
            if i == max_retries - 1:
                raise
            logger.debug(f"Waiting {retry_interval} seconds before next attempt")
            time.sleep(retry_interval)
    logger.debug("wait_for_server completed")

@contextmanager
def run_server():
    """Run the FastAPI server in a separate thread"""
    logger.debug("Starting run_server")
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    logger.debug("Created uvicorn server, starting thread")
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    try:
        logger.debug("Waiting for server to become available")
        wait_for_server()
        logger.debug("Server is available, yielding")
        yield
    finally:
        logger.debug("run_server cleanup")
        # Server will be killed when the thread is daemon
        pass

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment (database and server) is running before any tests"""
    logger.debug("Starting setup_test_environment")
    try:
        logger.debug("Waiting for database")
        wait_for_db()
        logger.debug("Database is ready, starting server")
        with run_server():
            logger.debug("Server is running, yielding to tests")
            yield
    except Exception as e:
        logger.error(f"Error in setup_test_environment: {str(e)}")
        raise
    finally:
        logger.debug("setup_test_environment cleanup completed")

# Use test database for testing
TEST_SQLALCHEMY_DATABASE_URL = str(settings.DATABASE_URL)

engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create database engine and tables"""
    logger.debug("Starting db_engine fixture")
    try:
        logger.debug("Getting engine from wait_for_db")
        engine = wait_for_db()
        logger.debug("Engine created successfully")
        yield engine
    finally:
        logger.debug("Starting db_engine cleanup")
        # Clean up
        Base.metadata.drop_all(bind=engine)
        logger.debug("db_engine cleanup completed")

@pytest.fixture(scope="function")
def db(db_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    logger.debug("Starting to create new database session")
    connection = db_engine.connect()
    logger.debug("Database connection established")
    transaction = connection.begin()
    logger.debug("Transaction begun")
    session = TestingSessionLocal(bind=connection)
    logger.debug("Session created")
    
    try:
        logger.debug("Yielding database session to test")
        yield session
    finally:
        logger.debug("Starting database session cleanup")
        try:
            logger.debug("Closing session")
            session.close()
            logger.debug("Rolling back transaction")
            transaction.rollback()
            logger.debug("Closing connection")
            connection.close()
            logger.debug("Database session cleanup completed")
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
            raise

@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override"""
    logger.debug("Starting client fixture setup")
    try:
        def override_get_db():
            logger.debug("override_get_db called")
            try:
                logger.debug("Yielding db session")
                yield db
            finally:
                logger.debug("override_get_db cleanup")
                pass  # Don't close the session here, it's managed by the db fixture
        
        logger.debug("Setting up dependency override")
        app.dependency_overrides[get_db] = override_get_db
        logger.debug("Creating TestClient")
        with TestClient(app) as test_client:
            logger.debug("TestClient created, yielding")
            yield test_client
        logger.debug("TestClient context exited")
    finally:
        logger.debug("Clearing dependency overrides")
        app.dependency_overrides.clear()
        logger.debug("Client fixture cleanup completed")

@pytest.fixture(scope="function")
def test_user(db: Session) -> User:
    """Create a test user for each test"""
    logger.debug("Starting test_user fixture setup")
    try:
        logger.debug("Creating User object")
        user = User(
            username="testuser",
            email="test@example.com",
            is_active=True
        )
        logger.debug("Setting user password")
        user.set_password("testpassword123")
        logger.debug("Adding user to session")
        db.add(user)
        logger.debug("Committing user to database")
        db.commit()
        logger.debug("Refreshing user from database")
        db.refresh(user)
        logger.debug(f"Successfully created test user with id: {user.id}")
        return user
    except Exception as e:
        logger.error(f"Error in test_user fixture: {str(e)}")
        raise

@pytest.fixture(scope="function")
def test_user_token(test_user: User) -> Dict[str, str]:
    access_token = security.create_access_token(test_user.id)
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def test_user_client(client: TestClient, test_user_token: Dict[str, str]) -> TestClient:
    client.headers = test_user_token
    return client 