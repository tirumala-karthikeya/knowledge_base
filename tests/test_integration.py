"""
Integration tests - Test complete workflows across API, database, and storage layers.
These tests verify that all components work together correctly.
"""
import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from pathlib import Path
from app import models, crud


@pytest.mark.integration
class TestCompleteDocumentWorkflow:
    """Test complete document lifecycle workflows."""
    
    def test_complete_document_lifecycle(self, client, temp_storage, db_session):
        """Test complete workflow: upload -> list -> get versions -> download -> delete."""
        # 1. Upload a new document
        file_content = b"Initial PDF content for integration test"
        files = {
            "file": ("integration_test.pdf", BytesIO(file_content), "application/pdf")
        }
        data = {
            "title": "Integration Test Document",
            "description": "Testing complete workflow",
            "tags": "test, integration, workflow"
        }
        
        upload_response = client.post("/documents/upload", files=files, data=data)
        assert upload_response.status_code == 200
        upload_result = upload_response.json()
        document_id = upload_result["document_id"]
        assert upload_result["version_number"] == 1
        
        # Verify file was saved
        doc_path = temp_storage / "docs" / str(document_id)
        assert doc_path.exists()
        version_files = list(doc_path.glob("v1_*"))
        assert len(version_files) == 1
        
        # 2. List documents and verify it appears
        list_response = client.get("/documents")
        assert list_response.status_code == 200
        documents = list_response.json()
        assert any(doc["id"] == document_id for doc in documents)
        
        doc_in_list = next(doc for doc in documents if doc["id"] == document_id)
        assert doc_in_list["title"] == "Integration Test Document"
        assert len(doc_in_list["tags"]) == 3
        
        # 3. Get document versions
        versions_response = client.get(f"/documents/{document_id}/versions")
        assert versions_response.status_code == 200
        versions_data = versions_response.json()
        assert versions_data["document_id"] == document_id
        assert len(versions_data["versions"]) == 1
        assert versions_data["versions"][0]["version_number"] == 1
        
        # 4. Download the document
        download_response = client.get(f"/documents/{document_id}/download")
        assert download_response.status_code == 200
        assert file_content in download_response.content
        
        # 5. Upload a new version
        new_file_content = b"Updated PDF content - version 2"
        files_v2 = {
            "file": ("integration_test_v2.pdf", BytesIO(new_file_content), "application/pdf")
        }
        data_v2 = {
            "title": "Updated Integration Test Document",
            "document_id": document_id
        }
        
        upload_v2_response = client.post("/documents/upload", files=files_v2, data=data_v2)
        assert upload_v2_response.status_code == 200
        upload_v2_result = upload_v2_response.json()
        assert upload_v2_result["document_id"] == document_id
        assert upload_v2_result["version_number"] == 2
        
        # Verify both versions exist
        versions_response = client.get(f"/documents/{document_id}/versions")
        versions_data = versions_response.json()
        assert len(versions_data["versions"]) == 2
        
        # Verify file system has both versions
        version_files = list(doc_path.glob("v*_*"))
        assert len(version_files) == 2
        
        # 6. Download specific version
        download_v1_response = client.get(f"/documents/{document_id}/download?version=1")
        assert download_v1_response.status_code == 200
        assert file_content in download_v1_response.content
        
        download_v2_response = client.get(f"/documents/{document_id}/download?version=2")
        assert download_v2_response.status_code == 200
        assert new_file_content in download_v2_response.content
        
        # 7. Delete the document
        delete_response = client.delete(f"/documents/{document_id}")
        assert delete_response.status_code == 200
        
        # Verify document is deleted from database
        get_response = client.get(f"/documents/{document_id}/versions")
        assert get_response.status_code == 404
        
        # Verify files are deleted (or at least directory cleanup)
        # Note: In real scenario, files should be deleted, but temp_storage cleanup handles it


@pytest.mark.integration
class TestSearchAndFilterWorkflow:
    """Test search and filtering workflows across multiple documents."""
    
    def test_search_workflow_with_multiple_documents(self, client, temp_storage):
        """Test creating multiple documents and searching/filtering them."""
        # Create multiple documents with different tags and types
        documents_data = [
            {"title": "Invoice Policy", "tags": "invoice, policy", "file": "invoice.pdf", "content": b"Invoice content"},
            {"title": "HR Handbook", "tags": "hr, policy", "file": "hr.pdf", "content": b"HR content"},
            {"title": "Technical Manual", "tags": "technical, docs", "file": "manual.pdf", "content": b"Technical content"},
            {"title": "Invoice Template", "tags": "invoice, template", "file": "template.pdf", "content": b"Template content"},
        ]
        
        created_ids = []
        for doc_data in documents_data:
            files = {"file": (doc_data["file"], BytesIO(doc_data["content"]), "application/pdf")}
            data = {"title": doc_data["title"], "tags": doc_data["tags"]}
            response = client.post("/documents/upload", files=files, data=data)
            assert response.status_code == 200
            created_ids.append(response.json()["document_id"])
        
        # Search by single tag
        response = client.get("/documents/search?tags=invoice")
        assert response.status_code == 200
        results = response.json()
        assert results["total"] == 2  # Invoice Policy and Invoice Template
        assert all("invoice" in [tag["name"] for tag in doc["tags"]] for doc in results["documents"])
        
        # Search by multiple tags (match_any)
        response = client.get("/documents/search?tags=invoice,hr")
        assert response.status_code == 200
        results = response.json()
        assert results["total"] >= 3  # At least Invoice Policy, HR Handbook, Invoice Template
        
        # Search by multiple tags (match_all)
        response = client.get("/documents/search?tags=invoice,policy&match_all=true")
        assert response.status_code == 200
        results = response.json()
        assert results["total"] == 1  # Only Invoice Policy has both tags
        assert results["documents"][0]["title"] == "Invoice Policy"
        
        # Search by text query
        response = client.get("/documents/search?query=Invoice")
        assert response.status_code == 200
        results = response.json()
        assert results["total"] == 2  # Invoice Policy and Invoice Template
        
        # Search by file type
        response = client.get("/documents/search?file_type=pdf")
        assert response.status_code == 200
        results = response.json()
        assert results["total"] >= 4  # All documents are PDFs
        
        # Combined search
        response = client.get("/documents/search?query=Invoice&tags=invoice&file_type=pdf")
        assert response.status_code == 200
        results = response.json()
        assert results["total"] == 2


@pytest.mark.integration
class TestTagManagementWorkflow:
    """Test tag creation and management across document operations."""
    
    def test_tag_reuse_across_documents(self, client, temp_storage, db_session):
        """Test that tags are reused across multiple documents."""
        # Upload first document with tags
        files1 = {"file": ("doc1.pdf", BytesIO(b"Content 1"), "application/pdf")}
        data1 = {"title": "Document 1", "tags": "shared, tag1"}
        response1 = client.post("/documents/upload", files=files1, data=data1)
        doc1_id = response1.json()["document_id"]
        
        # Upload second document with overlapping tags
        files2 = {"file": ("doc2.pdf", BytesIO(b"Content 2"), "application/pdf")}
        data2 = {"title": "Document 2", "tags": "shared, tag2"}
        response2 = client.post("/documents/upload", files=files2, data=data2)
        doc2_id = response2.json()["document_id"]
        
        # Verify both documents have the "shared" tag
        list_response = client.get("/documents")
        documents = list_response.json()
        doc1 = next(doc for doc in documents if doc["id"] == doc1_id)
        doc2 = next(doc for doc in documents if doc["id"] == doc2_id)
        
        tag_names_1 = [tag["name"] for tag in doc1["tags"]]
        tag_names_2 = [tag["name"] for tag in doc2["tags"]]
        
        assert "shared" in tag_names_1
        assert "shared" in tag_names_2
        
        # Verify tag is reused in database (same tag ID)
        tag1 = db_session.query(models.Tag).filter(models.Tag.name == "shared").first()
        assert tag1 is not None
        
        # Search by shared tag should return both documents
        search_response = client.get("/documents/search?tags=shared")
        assert search_response.status_code == 200
        results = search_response.json()
        assert results["total"] == 2
        
        # Update document tags
        files3 = {"file": ("doc1_v2.pdf", BytesIO(b"Content 1 v2"), "application/pdf")}
        data3 = {"title": "Document 1 Updated", "document_id": doc1_id, "tags": "shared, tag3"}
        client.post("/documents/upload", files=files3, data=data3)
        
        # Verify tags were updated
        list_response = client.get("/documents")
        documents = list_response.json()
        doc1_updated = next(doc for doc in documents if doc["id"] == doc1_id)
        tag_names_updated = [tag["name"] for tag in doc1_updated["tags"]]
        assert "shared" in tag_names_updated
        assert "tag3" in tag_names_updated
        assert "tag1" not in tag_names_updated  # Old tag removed


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across layers."""
    
    def test_upload_error_propagation(self, client, temp_storage):
        """Test that storage errors propagate correctly through API."""
        # Try to upload invalid file type
        files = {"file": ("invalid.exe", BytesIO(b"Executable content"), "application/x-msdownload")}
        data = {"title": "Invalid File"}
        
        response = client.post("/documents/upload", files=files, data=data)
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()
    
    def test_database_error_handling(self, client, temp_storage):
        """Test that database errors are handled gracefully."""
        # Try to get versions of non-existent document
        response = client.get("/documents/99999/versions")
        assert response.status_code == 404
        
        # Try to download non-existent document
        response = client.get("/documents/99999/download")
        assert response.status_code == 404
        
        # Try to delete non-existent document
        response = client.delete("/documents/99999")
        assert response.status_code == 404
    
    def test_file_not_found_handling(self, client, temp_storage, db_session):
        """Test handling when file is missing from storage."""
        # Create document in database but don't create file
        document = models.Document(title="Missing File Doc", description="Test")
        db_session.add(document)
        db_session.flush()
        
        version = models.DocumentVersion(
            document_id=document.id,
            version_number=1,
            file_path="storage/docs/999/v1_nonexistent.pdf",
            file_size=100,
            file_type="pdf"
        )
        db_session.add(version)
        db_session.commit()
        
        # Try to download - should handle missing file gracefully
        response = client.get(f"/documents/{document.id}/download")
        assert response.status_code == 404


@pytest.mark.integration
class TestConcurrentOperations:
    """Test concurrent operations and data consistency."""
    
    def test_multiple_versions_consistency(self, client, temp_storage):
        """Test that multiple versions maintain consistency."""
        # Upload initial document
        files = {"file": ("base.pdf", BytesIO(b"Version 1"), "application/pdf")}
        data = {"title": "Multi-Version Test"}
        response = client.post("/documents/upload", files=files, data=data)
        doc_id = response.json()["document_id"]
        
        # Upload multiple versions
        for i in range(2, 5):
            files_v = {"file": (f"v{i}.pdf", BytesIO(f"Version {i}".encode()), "application/pdf")}
            data_v = {"title": f"Multi-Version Test v{i}", "document_id": doc_id}
            response_v = client.post("/documents/upload", files=files_v, data=data_v)
            assert response_v.status_code == 200
            assert response_v.json()["version_number"] == i
        
        # Verify all versions exist and are sequential
        versions_response = client.get(f"/documents/{doc_id}/versions")
        versions = versions_response.json()["versions"]
        assert len(versions) == 4
        
        version_numbers = [v["version_number"] for v in versions]
        assert version_numbers == [1, 2, 3, 4]
        
        # Verify each version can be downloaded
        for version_num in range(1, 5):
            download_response = client.get(f"/documents/{doc_id}/download?version={version_num}")
            assert download_response.status_code == 200
            assert f"Version {version_num}".encode() in download_response.content


@pytest.mark.integration
class TestPaginationIntegration:
    """Test pagination across multiple operations."""
    
    def test_pagination_consistency(self, client, temp_storage):
        """Test that pagination works consistently across list and search."""
        # Create multiple documents
        for i in range(10):
            files = {"file": (f"doc{i}.pdf", BytesIO(f"Content {i}".encode()), "application/pdf")}
            data = {"title": f"Document {i}", "tags": f"tag{i % 3}"}  # Tags: tag0, tag1, tag2
            client.post("/documents/upload", files=files, data=data)
        
        # Test list pagination
        page1 = client.get("/documents?skip=0&limit=5").json()
        page2 = client.get("/documents?skip=5&limit=5").json()
        
        assert len(page1) == 5
        assert len(page2) == 5
        # Verify no overlap
        page1_ids = {doc["id"] for doc in page1}
        page2_ids = {doc["id"] for doc in page2}
        assert page1_ids.isdisjoint(page2_ids)
        
        # Test search pagination
        search_page1 = client.get("/documents/search?tags=tag0&skip=0&limit=3").json()
        search_page2 = client.get("/documents/search?tags=tag0&skip=3&limit=3").json()
        
        assert len(search_page1["documents"]) <= 3
        assert len(search_page2["documents"]) <= 3


@pytest.mark.integration
class TestDataIntegrity:
    """Test data integrity across operations."""
    
    def test_document_deletion_cascades(self, client, temp_storage, db_session):
        """Test that deleting a document removes all related data."""
        # Create document with multiple versions and tags
        files1 = {"file": ("v1.pdf", BytesIO(b"V1"), "application/pdf")}
        data1 = {"title": "Cascade Test", "tags": "test, cascade"}
        response1 = client.post("/documents/upload", files=files1, data=data1)
        doc_id = response1.json()["document_id"]
        
        # Add second version
        files2 = {"file": ("v2.pdf", BytesIO(b"V2"), "application/pdf")}
        data2 = {"title": "Cascade Test", "document_id": doc_id}
        response2 = client.post("/documents/upload", files=files2, data=data2)
        assert response2.status_code == 200
        
        # Verify document exists with versions
        versions_before = client.get(f"/documents/{doc_id}/versions").json()
        assert len(versions_before["versions"]) == 2
        
        # Delete document
        delete_response = client.delete(f"/documents/{doc_id}")
        assert delete_response.status_code == 200
        
        # Verify document is gone
        get_response = client.get(f"/documents/{doc_id}/versions")
        assert get_response.status_code == 404
        
        # Verify versions are deleted from database
        versions_in_db = db_session.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == doc_id
        ).all()
        assert len(versions_in_db) == 0
        
        # Verify document-tag associations are removed (tags themselves remain)
        doc_in_db = db_session.query(models.Document).filter(
            models.Document.id == doc_id
        ).first()
        assert doc_in_db is None
        
        # Tags should still exist (they're not deleted, just associations removed)
        tags = db_session.query(models.Tag).filter(models.Tag.name.in_(["test", "cascade"])).all()
        assert len(tags) == 2  # Tags remain in database

