import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models.user import User
from utils.security import hash_password, create_access_token


TEST_DATABASE_URL = "sqlite:///./test_fitlog.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db):
    user = User(
        username="testuser",
        email="testuser@example.com",
        display_name="Test User",
        password_hash=hash_password("testpassword123"),
        role="user",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(test_db):
    user = User(
        username="adminuser",
        email="adminuser@example.com",
        display_name="Admin User",
        password_hash=hash_password("adminpassword123"),
        role="admin",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def authenticated_client(test_client, test_user):
    access_token = create_access_token(data={"sub": str(test_user.id)})
    test_client.cookies.set("access_token", f"Bearer {access_token}")
    return test_client


@pytest.fixture(scope="function")
def admin_client(test_client, admin_user):
    access_token = create_access_token(data={"sub": str(admin_user.id)})
    test_client.cookies.set("access_token", f"Bearer {access_token}")
    return test_client