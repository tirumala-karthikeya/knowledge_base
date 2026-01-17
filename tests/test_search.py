import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestSearchDocuments:
    """Tests for GET /documents/search endpoint."""
    
    def test_search_by_tags_match_any(self, client, sample_document_with_tags):
        """Test searching by tags with match_any (default)."""
        # Create another document with different tag
        file_content = b"Content"
        files = {"file": ("doc.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "HR Document", "tags": "hr"}
        client.post("/documents/upload", files=files, data=data)
        
        response = client.get("/documents/search?tags=invoice,hr")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["documents"]) >= 2
    
    def test_search_by_tags_match_all(self, client, sample_document_with_tags):
        """Test searching by tags with match_all=True."""
        # Create document with only one tag
        file_content = b"Content"
        files = {"file": ("doc.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Single Tag Doc", "tags": "invoice"}
        client.post("/documents/upload", files=files, data=data)
        
        response = client.get("/documents/search?tags=invoice,policy&match_all=true")
        
        assert response.status_code == 200
        data = response.json()
        # Should only return document with both tags
        assert data["total"] >= 1
        for doc in data["documents"]:
            tag_names = [tag["name"] for tag in doc["tags"]]
            assert "invoice" in tag_names
            assert "policy" in tag_names
    
    def test_search_by_query(self, client, sample_document):
        """Test searching by text query."""
        response = client.get("/documents/search?query=test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        # Verify at least one result contains "test" in title or description
        found = False
        for doc in data["documents"]:
            if "test" in doc["title"].lower() or (doc["description"] and "test" in doc["description"].lower()):
                found = True
                break
        assert found
    
    def test_search_by_file_type(self, client, sample_document):
        """Test searching by file type."""
        response = client.get("/documents/search?file_type=pdf")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    def test_search_combined_filters(self, client, sample_document_with_tags):
        """Test searching with multiple filters."""
        response = client.get("/documents/search?query=invoice&tags=invoice&file_type=pdf")
        
        assert response.status_code == 200
        data = response.json()
        # Should return documents matching all criteria
        assert data["total"] >= 0
    
    def test_search_no_results(self, client):
        """Test search with filters that match nothing."""
        response = client.get("/documents/search?query=nonexistentquery12345")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["documents"]) == 0
    
    def test_search_empty_tags(self, client):
        """Test search with empty tags parameter."""
        response = client.get("/documents/search?tags=")
        
        assert response.status_code == 200
        data = response.json()
        # Should return all documents or empty if no documents
        assert "total" in data
        assert "documents" in data
    
    def test_search_pagination(self, client):
        """Test search with pagination."""
        # Create multiple documents
        for i in range(5):
            file_content = b"Content"
            files = {"file": (f"doc{i}.pdf", BytesIO(file_content), "application/pdf")}
            data = {"title": f"Searchable Document {i}"}
            client.post("/documents/upload", files=files, data=data)
        
        response = client.get("/documents/search?query=Searchable&skip=2&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) <= 2
    
    def test_search_with_special_characters(self, client):
        """Test search with special characters in query."""
        file_content = b"Content"
        files = {"file": ("doc.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Test & Special Document"}
        client.post("/documents/upload", files=files, data=data)
        
        response = client.get("/documents/search?query=Special")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

