import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestUploadDocument:
    """Tests for POST /documents/upload endpoint."""
    
    def test_upload_new_document(self, client, temp_storage):
        """Test uploading a new document."""
        file_content = b"Test PDF content"
        files = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }
        data = {
            "title": "Test Document",
            "description": "Test description",
            "tags": "invoice, policy"
        }
        
        response = client.post("/documents/upload", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "document_id" in result
        assert result["version_number"] == 1
        assert "successfully" in result["message"].lower()
    
    def test_upload_document_without_tags(self, client, temp_storage):
        """Test uploading document without tags."""
        file_content = b"Test content"
        files = {
            "file": ("test.txt", BytesIO(file_content), "text/plain")
        }
        data = {
            "title": "No Tags Document"
        }
        
        response = client.post("/documents/upload", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["document_id"] is not None
    
    def test_upload_document_missing_title(self, client, temp_storage):
        """Test uploading document without required title."""
        file_content = b"Test content"
        files = {
            "file": ("test.pdf", BytesIO(file_content), "application/pdf")
        }
        data = {}
        
        response = client.post("/documents/upload", files=files, data=data)
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_document_missing_file(self, client):
        """Test uploading document without file."""
        data = {
            "title": "Test Document"
        }
        
        response = client.post("/documents/upload", data=data)
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_new_version(self, client, temp_storage, sample_document):
        """Test uploading a new version to existing document."""
        file_content = b"New version content"
        files = {
            "file": ("v2.pdf", BytesIO(file_content), "application/pdf")
        }
        data = {
            "title": "Updated Title",
            "document_id": sample_document.id
        }
        
        response = client.post("/documents/upload", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["document_id"] == sample_document.id
        assert result["version_number"] == 2


class TestListDocuments:
    """Tests for GET /documents endpoint."""
    
    def test_list_documents_empty(self, client):
        """Test listing documents when database is empty."""
        response = client.get("/documents")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_documents_with_data(self, client, sample_document):
        """Test listing documents."""
        response = client.get("/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_document.id
        assert data[0]["title"] == sample_document.title
    
    def test_list_documents_pagination(self, client):
        """Test pagination parameters."""
        # Create multiple documents
        for i in range(5):
            file_content = b"Content"
            files = {"file": (f"doc{i}.pdf", BytesIO(file_content), "application/pdf")}
            data = {"title": f"Document {i}"}
            client.post("/documents/upload", files=files, data=data)
        
        # Test pagination
        response = client.get("/documents?skip=2&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_list_documents_includes_tags(self, client, sample_document_with_tags):
        """Test that listed documents include tags."""
        response = client.get("/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        doc = next((d for d in data if d["id"] == sample_document_with_tags.id), None)
        assert doc is not None
        assert len(doc["tags"]) == 2


class TestGetVersions:
    """Tests for GET /documents/{document_id}/versions endpoint."""
    
    def test_get_versions_existing_document(self, client, sample_document_multiple_versions):
        """Test getting versions for document with multiple versions."""
        response = client.get(f"/documents/{sample_document_multiple_versions.id}/versions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document_multiple_versions.id
        assert len(data["versions"]) == 3
        assert data["versions"][0]["version_number"] == 1
        assert data["versions"][2]["version_number"] == 3
    
    def test_get_versions_nonexistent_document(self, client):
        """Test getting versions for non-existent document."""
        response = client.get("/documents/99999/versions")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDownloadDocument:
    """Tests for GET /documents/{document_id}/download endpoint."""
    
    def test_download_latest_version(self, client, temp_storage, sample_document):
        """Test downloading latest version of document."""
        # Create actual file for download
        doc_path = temp_storage / "docs" / str(sample_document.id)
        doc_path.mkdir(parents=True, exist_ok=True)
        test_file = doc_path / "v1_test.pdf"
        test_file.write_bytes(b"PDF content for download")
        
        response = client.get(f"/documents/{sample_document.id}/download")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert b"PDF content" in response.content
    
    def test_download_specific_version(self, client, temp_storage, sample_document_multiple_versions):
        """Test downloading specific version."""
        # Create actual files
        doc_path = temp_storage / "docs" / str(sample_document_multiple_versions.id)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v2_test.pdf").write_bytes(b"Version 2 content")
        
        response = client.get(
            f"/documents/{sample_document_multiple_versions.id}/download?version=2"
        )
        
        assert response.status_code == 200
        assert b"Version 2" in response.content
    
    def test_download_nonexistent_document(self, client):
        """Test downloading non-existent document."""
        response = client.get("/documents/99999/download")
        
        assert response.status_code == 404
    
    def test_download_nonexistent_version(self, client, temp_storage, sample_document):
        """Test downloading non-existent version."""
        # Create file for v1 but request v5
        doc_path = temp_storage / "docs" / str(sample_document.id)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v1_test.pdf").write_bytes(b"Content")
        
        response = client.get(f"/documents/{sample_document.id}/download?version=5")
        
        assert response.status_code == 404


class TestPreviewDocument:
    """Tests for GET /documents/{document_id}/preview endpoint."""
    
    def test_preview_latest_version(self, client, temp_storage, sample_document):
        """Test previewing latest version."""
        # Create actual file
        doc_path = temp_storage / "docs" / str(sample_document.id)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v1_test.pdf").write_bytes(b"PDF preview content")
        
        response = client.get(f"/documents/{sample_document.id}/preview")
        
        assert response.status_code == 200
        assert "application/pdf" in response.headers["content-type"]
        assert "inline" in response.headers["content-disposition"]
    
    def test_preview_specific_version(self, client, temp_storage, sample_document_multiple_versions):
        """Test previewing specific version."""
        doc_path = temp_storage / "docs" / str(sample_document_multiple_versions.id)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v2_test.pdf").write_bytes(b"Version 2 preview")
        
        response = client.get(
            f"/documents/{sample_document_multiple_versions.id}/preview?version=2"
        )
        
        assert response.status_code == 200
        assert "inline" in response.headers["content-disposition"]
    
    def test_preview_nonexistent_document(self, client):
        """Test previewing non-existent document."""
        response = client.get("/documents/99999/preview")
        
        assert response.status_code == 404


class TestDeleteDocument:
    """Tests for DELETE /documents/{document_id} endpoint."""
    
    def test_delete_existing_document(self, client, temp_storage, sample_document):
        """Test deleting an existing document."""
        # Create file for document
        doc_path = temp_storage / "docs" / str(sample_document.id)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v1_test.pdf").write_bytes(b"Content")
        
        response = client.delete(f"/documents/{sample_document.id}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()
        
        # Verify document is deleted
        get_response = client.get(f"/documents/{sample_document.id}/versions")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_document(self, client):
        """Test deleting non-existent document."""
        response = client.delete("/documents/99999")
        
        assert response.status_code == 404

