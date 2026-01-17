import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO
from unittest.mock import Mock, patch

from app import crud, models, schemas


class TestGetOrCreateTag:
    """Tests for get_or_create_tag function."""
    
    def test_get_existing_tag(self, db_session):
        """Test retrieving an existing tag."""
        # Create tag
        tag = models.Tag(name="invoice")
        db_session.add(tag)
        db_session.commit()
        
        # Get tag
        result = crud.get_or_create_tag(db_session, "invoice")
        
        assert result.name == "invoice"
        assert result.id == tag.id
    
    def test_create_new_tag(self, db_session):
        """Test creating a new tag."""
        result = crud.get_or_create_tag(db_session, "policy")
        
        assert result.name == "policy"
        assert result.id is not None
    
    def test_tag_name_normalization(self, db_session):
        """Test that tag names are normalized (lowercase, trimmed)."""
        result = crud.get_or_create_tag(db_session, "  INVOICE  ")
        
        assert result.name == "invoice"
    
    def test_tag_case_insensitive(self, db_session):
        """Test that tag lookup is case insensitive."""
        tag = models.Tag(name="invoice")
        db_session.add(tag)
        db_session.commit()
        
        result = crud.get_or_create_tag(db_session, "INVOICE")
        
        assert result.id == tag.id
        assert result.name == "invoice"


class TestCreateDocument:
    """Tests for create_document function."""
    
    @patch('app.crud.save_file')
    def test_create_document_basic(self, mock_save_file, db_session, upload_file_pdf):
        """Test creating a document without tags."""
        mock_save_file.return_value = ("storage/docs/1/v1_test.pdf", 1024)
        
        result = crud.create_document(
            db=db_session,
            title="Test Document",
            description="Test description",
            tags_string=None,
            file=upload_file_pdf
        )
        
        assert result.document_id is not None
        assert result.version_number == 1
        assert "successfully" in result.message.lower()
        
        # Verify document in database
        document = db_session.query(models.Document).filter(
            models.Document.id == result.document_id
        ).first()
        assert document is not None
        assert document.title == "Test Document"
        assert document.description == "Test description"
        
        # Verify version in database
        version = db_session.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == result.document_id
        ).first()
        assert version is not None
        assert version.version_number == 1
    
    @patch('app.crud.save_file')
    def test_create_document_with_tags(self, mock_save_file, db_session, upload_file_pdf):
        """Test creating a document with tags."""
        mock_save_file.return_value = ("storage/docs/1/v1_test.pdf", 1024)
        
        result = crud.create_document(
            db=db_session,
            title="Tagged Document",
            description=None,
            tags_string="invoice, policy, hr",
            file=upload_file_pdf
        )
        
        document = db_session.query(models.Document).filter(
            models.Document.id == result.document_id
        ).first()
        
        assert len(document.tags) == 3
        tag_names = [tag.name for tag in document.tags]
        assert "invoice" in tag_names
        assert "policy" in tag_names
        assert "hr" in tag_names
    
    @patch('app.crud.save_file')
    def test_create_document_empty_tags(self, mock_save_file, db_session, upload_file_pdf):
        """Test creating a document with empty tags string."""
        mock_save_file.return_value = ("storage/docs/1/v1_test.pdf", 1024)
        
        result = crud.create_document(
            db=db_session,
            title="No Tags Document",
            description=None,
            tags_string="  ,  ,  ",
            file=upload_file_pdf
        )
        
        document = db_session.query(models.Document).filter(
            models.Document.id == result.document_id
        ).first()
        
        assert len(document.tags) == 0


class TestAddDocumentVersion:
    """Tests for add_document_version function."""
    
    @patch('app.crud.save_file')
    def test_add_version_to_existing_document(self, mock_save_file, db_session, sample_document, upload_file_pdf):
        """Test adding a new version to an existing document."""
        mock_save_file.return_value = ("storage/docs/1/v2_test.pdf", 2048)
        
        result = crud.add_document_version(
            db=db_session,
            document_id=sample_document.id,
            file=upload_file_pdf
        )
        
        assert result.document_id == sample_document.id
        assert result.version_number == 2
        
        # Verify new version exists
        versions = db_session.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == sample_document.id
        ).all()
        assert len(versions) == 2
    
    @patch('app.crud.save_file')
    def test_add_version_updates_metadata(self, mock_save_file, db_session, sample_document, upload_file_pdf):
        """Test that adding version can update document metadata."""
        mock_save_file.return_value = ("storage/docs/1/v2_test.pdf", 2048)
        
        result = crud.add_document_version(
            db=db_session,
            document_id=sample_document.id,
            file=upload_file_pdf,
            title="Updated Title",
            description="Updated description",
            tags_string="new, tags"
        )
        
        db_session.refresh(sample_document)
        assert sample_document.title == "Updated Title"
        assert sample_document.description == "Updated description"
        assert len(sample_document.tags) == 2
    
    @patch('app.crud.save_file')
    def test_add_version_replaces_tags(self, mock_save_file, db_session, sample_document_with_tags, upload_file_pdf):
        """Test that adding version replaces existing tags."""
        mock_save_file.return_value = ("storage/docs/1/v2_test.pdf", 2048)
        
        # Document initially has 2 tags
        assert len(sample_document_with_tags.tags) == 2
        
        result = crud.add_document_version(
            db=db_session,
            document_id=sample_document_with_tags.id,
            file=upload_file_pdf,
            tags_string="single, tag"
        )
        
        db_session.refresh(sample_document_with_tags)
        assert len(sample_document_with_tags.tags) == 2
        tag_names = [tag.name for tag in sample_document_with_tags.tags]
        assert "single" in tag_names
        assert "tag" in tag_names
        assert "invoice" not in tag_names
    
    def test_add_version_document_not_found(self, db_session, upload_file_pdf):
        """Test adding version to non-existent document raises error."""
        with pytest.raises(HTTPException) as exc_info:
            crud.add_document_version(
                db=db_session,
                document_id=99999,
                file=upload_file_pdf
            )
        
        assert exc_info.value.status_code == 404


class TestGetDocuments:
    """Tests for get_documents function."""
    
    def test_get_documents_empty(self, db_session):
        """Test getting documents when database is empty."""
        result = crud.get_documents(db_session)
        assert len(result) == 0
    
    def test_get_documents_with_data(self, db_session, sample_document):
        """Test getting documents."""
        result = crud.get_documents(db_session)
        assert len(result) == 1
        assert result[0].id == sample_document.id
    
    def test_get_documents_pagination(self, db_session):
        """Test pagination."""
        # Create multiple documents
        for i in range(5):
            doc = models.Document(title=f"Document {i}", description=f"Desc {i}")
            db_session.add(doc)
        db_session.commit()
        
        # Test skip and limit
        result = crud.get_documents(db_session, skip=2, limit=2)
        assert len(result) == 2


class TestGetDocumentById:
    """Tests for get_document_by_id function."""
    
    def test_get_existing_document(self, db_session, sample_document):
        """Test getting an existing document."""
        result = crud.get_document_by_id(db_session, sample_document.id)
        assert result is not None
        assert result.id == sample_document.id
        assert result.title == sample_document.title
    
    def test_get_nonexistent_document(self, db_session):
        """Test getting a non-existent document."""
        result = crud.get_document_by_id(db_session, 99999)
        assert result is None


class TestGetDocumentVersions:
    """Tests for get_document_versions function."""
    
    def test_get_versions_existing_document(self, db_session, sample_document_multiple_versions):
        """Test getting versions for a document with multiple versions."""
        result = crud.get_document_versions(db_session, sample_document_multiple_versions.id)
        
        assert result is not None
        assert result.document_id == sample_document_multiple_versions.id
        assert len(result.versions) == 3
        assert result.versions[0].version_number == 1
        assert result.versions[2].version_number == 3
    
    def test_get_versions_nonexistent_document(self, db_session):
        """Test getting versions for non-existent document."""
        result = crud.get_document_versions(db_session, 99999)
        assert result is None
    
    def test_get_versions_single_version(self, db_session, sample_document):
        """Test getting versions for document with single version."""
        result = crud.get_document_versions(db_session, sample_document.id)
        
        assert result is not None
        assert len(result.versions) == 1
        assert result.versions[0].version_number == 1


class TestSearchDocumentsByTags:
    """Tests for search_documents_by_tags function."""
    
    def test_search_by_tags_match_any(self, db_session, sample_document_with_tags):
        """Test searching documents with match_any (default)."""
        # Create another document with different tag
        doc2 = models.Document(title="Other Doc", description="Other")
        tag3 = models.Tag(name="hr")
        db_session.add(tag3)
        db_session.flush()
        doc2.tags.append(tag3)
        db_session.add(doc2)
        db_session.commit()
        
        # Search for invoice or hr
        result = crud.search_documents_by_tags(
            db_session,
            tags=["invoice", "hr"],
            match_all=False
        )
        
        assert len(result) == 2
    
    def test_search_by_tags_match_all(self, db_session, sample_document_with_tags):
        """Test searching documents with match_all=True."""
        # Create document with only one of the tags
        doc2 = models.Document(title="Partial Doc", description="Partial")
        tag = db_session.query(models.Tag).filter(models.Tag.name == "invoice").first()
        doc2.tags.append(tag)
        db_session.add(doc2)
        db_session.commit()
        
        # Search for documents with both invoice AND policy
        result = crud.search_documents_by_tags(
            db_session,
            tags=["invoice", "policy"],
            match_all=True
        )
        
        assert len(result) == 1
        assert result[0].id == sample_document_with_tags.id
    
    def test_search_by_tags_empty_list(self, db_session):
        """Test searching with empty tags list."""
        result = crud.search_documents_by_tags(db_session, tags=[])
        assert len(result) == 0
    
    def test_search_by_tags_nonexistent_tags(self, db_session):
        """Test searching with tags that don't exist."""
        result = crud.search_documents_by_tags(
            db_session,
            tags=["nonexistent", "tags"]
        )
        assert len(result) == 0


class TestSearchDocumentsAdvanced:
    """Tests for search_documents_advanced function."""
    
    def test_search_by_query(self, db_session, sample_document):
        """Test searching by text query."""
        result = crud.search_documents_advanced(
            db_session,
            query="test"
        )
        
        assert len(result) >= 1
        assert any("test" in doc.title.lower() or (doc.description and "test" in doc.description.lower()) 
                   for doc in result)
    
    def test_search_by_file_type(self, db_session, sample_document):
        """Test searching by file type."""
        result = crud.search_documents_advanced(
            db_session,
            file_type="pdf"
        )
        
        assert len(result) >= 1
    
    def test_search_combined_filters(self, db_session, sample_document_with_tags):
        """Test searching with multiple filters."""
        result = crud.search_documents_advanced(
            db_session,
            query="invoice",
            tags=["invoice"],
            file_type="pdf"
        )
        
        assert len(result) >= 1
    
    def test_search_no_results(self, db_session):
        """Test search with filters that match nothing."""
        result = crud.search_documents_advanced(
            db_session,
            query="nonexistentquery12345"
        )
        
        assert len(result) == 0


class TestDeleteDocument:
    """Tests for delete_document function."""
    
    @patch('app.crud.delete_document_files')
    def test_delete_existing_document(self, mock_delete_files, db_session, sample_document):
        """Test deleting an existing document."""
        doc_id = sample_document.id
        
        result = crud.delete_document(db_session, doc_id)
        
        assert result is True
        mock_delete_files.assert_called_once_with(doc_id)
        
        # Verify document is deleted
        deleted = db_session.query(models.Document).filter(
            models.Document.id == doc_id
        ).first()
        assert deleted is None
    
    @patch('app.crud.delete_document_files')
    def test_delete_document_cascades_versions(self, mock_delete_files, db_session, sample_document_multiple_versions):
        """Test that deleting document also deletes versions."""
        doc_id = sample_document_multiple_versions.id
        
        crud.delete_document(db_session, doc_id)
        
        # Verify versions are deleted
        versions = db_session.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == doc_id
        ).all()
        assert len(versions) == 0
    
    def test_delete_nonexistent_document(self, db_session):
        """Test deleting a non-existent document raises error."""
        with pytest.raises(HTTPException) as exc_info:
            crud.delete_document(db_session, 99999)
        
        assert exc_info.value.status_code == 404

