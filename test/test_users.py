import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.models import Base
from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite database for testing 
TEST_DB_URL = "sqlite://"

#  Create the test engine and session
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Create all tables for the test DB
Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    """Fixture to provide a test client with a temporary DB session."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c  # hand over the client to the test


def test_create_user(client):
    """Test that a new user can be created successfully."""
    r = client.post(
        "/api/users",
        json={
            "name": "Paul",
            "email": "pl@atu.ie",
            "age": 25,
            "student_id": "S1234567",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Paul"
    assert data["email"] == "pl@atu.ie"
    assert data["age"] == 25
    assert data["student_id"] == "S1234567"


def test_put_user_ok(client):
    """Test full replacement (PUT) of an existing user."""
    #  Create a user to update
    r_create = client.post(
        "/api/users",
        json={
            "name": "Eoin",
            "email": "eoin@atu.ie",
            "age": 21,
            "student_id": "S2468101",
        },
    )
    assert r_create.status_code == 201
    uid = r_create.json()["id"]

    # Prepare the full replacement payload
    updated = {
        "name": "Eoin Updated",
        "email": "eoin.updated@atu.ie",
        "age": 22,
        "student_id": "S2468101",
    }

    # Send PUT request to replace the user
    r = client.put(f"/api/users/{uid}", json=updated)
    assert r.status_code == 200

    #  Validate the response
    body = r.json()
    assert body["id"] == uid
    assert body["name"] == "Eoin Updated"
    assert body["email"] == "eoin.updated@atu.ie"
    assert body["age"] == 22
    assert body["student_id"] == "S2468101"


def test_put_user_404(client):
    """Test that PUT returns 404 when updating a non-existent user."""
    payload = {
        "name": "Ghost",
        "email": "ghost@atu.ie",
        "age": 99,
        "student_id": "S9999999",
    }

    r = client.put("/api/users/999999", json=payload)
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()
