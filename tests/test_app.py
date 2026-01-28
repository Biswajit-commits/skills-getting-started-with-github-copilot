"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities_returns_all_activities(self):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
        
        # Check that all expected activities are present
        expected_activities = [
            "Chess Club", "Basketball Team", "Tennis Club", "Art Studio",
            "Drama Club", "Debate Team", "Science Club", "Programming Class", "Gym Class"
        ]
        for activity in expected_activities:
            assert activity in activities

    def test_activities_have_required_fields(self):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            for field in required_fields:
                assert field in activity_data, f"Missing field '{field}' in {activity_name}"


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "message" in result
        assert "newstudent@mergington.edu" in result["message"]
        assert "Chess Club" in result["message"]

    def test_signup_adds_participant(self):
        """Test that signup actually adds the participant to the activity"""
        email = "testalumni@mergington.edu"
        
        # Sign up
        response = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities = client.get("/activities").json()
        assert email in activities["Basketball Team"]["participants"]

    def test_signup_duplicate_fails(self):
        """Test that signing up with duplicate email fails"""
        email = "duplicate@mergington.edu"
        
        # First signup succeeds
        response1 = client.post(
            f"/activities/Tennis Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup with same email fails
        response2 = client.post(
            f"/activities/Tennis Club/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_nonexistent_activity_fails(self):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_with_invalid_email(self):
        """Test signup with various email formats"""
        # FastAPI doesn't validate email format in query params by default
        # This test ensures the endpoint accepts the email parameter
        response = client.post(
            "/activities/Art Studio/signup?email=invalidemail"
        )
        assert response.status_code == 200  # Still accepts it


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self):
        """Test successful unregistration from an activity"""
        email = "unregistertest@mergington.edu"
        activity = "Drama Club"
        
        # First sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Then unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        result = unregister_response.json()
        assert "message" in result
        assert email in result["message"]
        assert activity in result["message"]

    def test_unregister_removes_participant(self):
        """Test that unregister actually removes the participant"""
        email = "removeme@mergington.edu"
        activity = "Science Club"
        
        # Sign up
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Verify added
        activities = client.get("/activities").json()
        assert email in activities[activity]["participants"]
        
        # Unregister
        client.post(f"/activities/{activity}/unregister?email={email}")
        
        # Verify removed
        activities = client.get("/activities").json()
        assert email not in activities[activity]["participants"]

    def test_unregister_not_registered_fails(self):
        """Test that unregistering a non-registered student fails"""
        response = client.post(
            "/activities/Programming Class/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_nonexistent_activity_fails(self):
        """Test that unregistering from non-existent activity fails"""
        response = client.post(
            "/activities/Fake Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self):
        """Test that root endpoint redirects to static HTML"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivityIntegration:
    """Integration tests for complete workflows"""

    def test_complete_signup_and_unregister_workflow(self):
        """Test a complete workflow: sign up and then unregister"""
        email = "workflow@mergington.edu"
        activity = "Gym Class"
        
        # Start - get initial count
        initial_activities = client.get("/activities").json()
        initial_count = len(initial_activities[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify count increased
        after_signup = client.get("/activities").json()
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify count back to initial
        after_unregister = client.get("/activities").json()
        assert len(after_unregister[activity]["participants"]) == initial_count

    def test_multiple_signups_to_different_activities(self):
        """Test signing up for multiple different activities"""
        email = "multiactivity@mergington.edu"
        activities_list = ["Chess Club", "Art Studio", "Science Club"]
        
        for activity in activities_list:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify in all activities
        activities = client.get("/activities").json()
        for activity in activities_list:
            assert email in activities[activity]["participants"]
