import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "endpoints" in data
        
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        
        # Verify endpoints list
        endpoints = data["endpoints"]
        assert "upload" in endpoints
        assert "list" in endpoints
        assert "search" in endpoints
        assert "versions" in endpoints
        assert "download" in endpoints

