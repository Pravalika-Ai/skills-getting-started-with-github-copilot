"""
Tests for the Mergington High School Activities API
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Fixture to provide a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Fixture to reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
    }
    
    # Clear activities and repopulate
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


# Root endpoint tests
def test_root_redirect(client):
    """Test that root endpoint redirects to static/index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


# Get activities tests
def test_get_activities(client, reset_activities):
    """Test retrieving all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert "Gym Class" in data


def test_get_activities_structure(client, reset_activities):
    """Test that activities have the correct structure"""
    response = client.get("/activities")
    data = response.json()
    activity = data["Chess Club"]
    
    assert "description" in activity
    assert "schedule" in activity
    assert "max_participants" in activity
    assert "participants" in activity
    assert isinstance(activity["participants"], list)


# Signup tests
def test_signup_success(client, reset_activities):
    """Test successful signup for an activity"""
    response = client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Signed up" in data["message"]
    
    # Verify participant was added
    activities_data = client.get("/activities").json()
    assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]


def test_signup_duplicate_email(client, reset_activities):
    """Test signup fails when student is already registered"""
    response = client.post("/activities/Chess Club/signup?email=michael@mergington.edu")
    assert response.status_code == 400
    data = response.json()
    assert "already signed up" in data["detail"]


def test_signup_nonexistent_activity(client, reset_activities):
    """Test signup fails for non-existent activity"""
    response = client.post("/activities/Nonexistent Club/signup?email=student@mergington.edu")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_signup_multiple_students(client, reset_activities):
    """Test multiple students can sign up for the same activity"""
    email1 = "student1@mergington.edu"
    email2 = "student2@mergington.edu"
    
    response1 = client.post(f"/activities/Programming Class/signup?email={email1}")
    assert response1.status_code == 200
    
    response2 = client.post(f"/activities/Programming Class/signup?email={email2}")
    assert response2.status_code == 200
    
    # Verify both were added
    activities_data = client.get("/activities").json()
    participants = activities_data["Programming Class"]["participants"]
    assert email1 in participants
    assert email2 in participants


# Unregister tests
def test_unregister_success(client, reset_activities):
    """Test successful unregister from an activity"""
    response = client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
    assert response.status_code == 200
    data = response.json()
    assert "Unregistered" in data["message"]
    
    # Verify participant was removed
    activities_data = client.get("/activities").json()
    assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]


def test_unregister_not_registered(client, reset_activities):
    """Test unregister fails for student not registered in activity"""
    response = client.delete("/activities/Chess Club/unregister?email=notregistered@mergington.edu")
    assert response.status_code == 400
    data = response.json()
    assert "not registered" in data["detail"]


def test_unregister_nonexistent_activity(client, reset_activities):
    """Test unregister fails for non-existent activity"""
    response = client.delete("/activities/Nonexistent Club/unregister?email=student@mergington.edu")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_unregister_then_signup_again(client, reset_activities):
    """Test that a student can unregister and sign up again"""
    email = "test@mergington.edu"
    activity = "Gym Class"
    
    # First signup
    response1 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response1.status_code == 200
    
    # Unregister
    response2 = client.delete(f"/activities/{activity}/unregister?email={email}")
    assert response2.status_code == 200
    
    # Sign up again
    response3 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response3.status_code == 200


# Integration tests
def test_signup_unregister_workflow(client, reset_activities):
    """Test complete signup and unregister workflow"""
    email = "workflow@mergington.edu"
    activity = "Programming Class"
    
    # Get initial participant count
    initial = client.get("/activities").json()
    initial_count = len(initial[activity]["participants"])
    
    # Sign up
    signup_response = client.post(f"/activities/{activity}/signup?email={email}")
    assert signup_response.status_code == 200
    
    # Verify count increased
    after_signup = client.get("/activities").json()
    assert len(after_signup[activity]["participants"]) == initial_count + 1
    assert email in after_signup[activity]["participants"]
    
    # Unregister
    unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
    assert unregister_response.status_code == 200
    
    # Verify count back to original
    after_unregister = client.get("/activities").json()
    assert len(after_unregister[activity]["participants"]) == initial_count
    assert email not in after_unregister[activity]["participants"]


def test_activities_isolation(client, reset_activities):
    """Test that changes to one activity don't affect others"""
    email = "isolated@mergington.edu"
    
    # Sign up for one activity
    response = client.post(f"/activities/Chess Club/signup?email={email}")
    assert response.status_code == 200
    
    # Verify only Chess Club was affected
    activities_data = client.get("/activities").json()
    assert email in activities_data["Chess Club"]["participants"]
    assert email not in activities_data["Programming Class"]["participants"]
    assert email not in activities_data["Gym Class"]["participants"]
