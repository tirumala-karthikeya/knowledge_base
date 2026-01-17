import pytest
from pathlib import Path
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app import storage


class TestValidateFile:
    """Tests for validate_file function."""
    
    def test_validate_pdf_file(self):
        """Test validating a PDF file."""
        file = BytesIO(b"PDF content")
        file.name = "test.pdf"
        file.content_type = "application/pdf"
        upload_file = UploadFile(file=file, filename="test.pdf")
        
        ext, filename = storage.validate_file(upload_file)
        
        assert ext == ".pdf"
        assert filename.endswith(".pdf")
        assert len(filename) > 4  # Should have UUID prefix
    
    def test_validate_txt_file(self):
        """Test validating a TXT file."""
        file = BytesIO(b"Text content")
        file.name = "test.txt"
        file.content_type = "text/plain"
        upload_file = UploadFile(file=file, filename="test.txt")
        
        ext, filename = storage.validate_file(upload_file)
        
        assert ext == ".txt"
        assert filename.endswith(".txt")
    
    def test_validate_docx_file(self):
        """Test validating a DOCX file."""
        file = BytesIO(b"DOCX content")
        file.name = "test.docx"
        file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        upload_file = UploadFile(file=file, filename="test.docx")
        
        ext, filename = storage.validate_file(upload_file)
        
        assert ext == ".docx"
        assert filename.endswith(".docx")
    
    def test_validate_invalid_extension(self):
        """Test that invalid file extension raises error."""
        file = BytesIO(b"Content")
        file.name = "test.exe"
        file.content_type = "application/x-msdownload"
        upload_file = UploadFile(file=file, filename="test.exe")
        
        with pytest.raises(HTTPException) as exc_info:
            storage.validate_file(upload_file)
        
        assert exc_info.value.status_code == 400
    
    def test_validate_no_filename(self):
        """Test that missing filename raises error."""
        file = BytesIO(b"Content")
        upload_file = UploadFile(file=file, filename="")
        
        with pytest.raises(HTTPException) as exc_info:
            storage.validate_file(upload_file)
        
        assert exc_info.value.status_code == 400
    
    def test_validate_invalid_mime_type(self):
        """Test that invalid MIME type raises error."""
        from unittest.mock import Mock
        
        # Create a mock UploadFile with wrong MIME type
        upload_file = Mock(spec=UploadFile)
        upload_file.filename = "test.pdf"
        upload_file.content_type = "application/x-msdownload"  # Wrong MIME type for PDF
        
        with pytest.raises(HTTPException) as exc_info:
            storage.validate_file(upload_file)
        
        assert exc_info.value.status_code == 400
        assert "MIME type" in exc_info.value.detail or "Invalid" in exc_info.value.detail


class TestValidateFileSize:
    """Tests for validate_file_size function."""
    
    def test_validate_small_file(self):
        """Test that small file passes validation."""
        storage.validate_file_size(1024)  # 1KB
    
    def test_validate_large_file(self):
        """Test that large file raises error."""
        large_size = storage.MAX_FILE_SIZE + 1
        
        with pytest.raises(HTTPException) as exc_info:
            storage.validate_file_size(large_size)
        
        assert exc_info.value.status_code == 400
        assert "exceeds" in exc_info.value.detail.lower()
    
    def test_validate_max_size_file(self):
        """Test that file at max size passes."""
        storage.validate_file_size(storage.MAX_FILE_SIZE)


class TestGetDocumentStoragePath:
    """Tests for get_document_storage_path function."""
    
    def test_get_storage_path(self):
        """Test getting storage path for document."""
        path = storage.get_document_storage_path(123)
        
        assert isinstance(path, Path)
        assert "123" in str(path)
        assert "docs" in str(path)


class TestSaveFile:
    """Tests for save_file function."""
    
    def test_save_file_creates_directory(self, temp_storage):
        """Test that save_file creates necessary directories."""
        file = BytesIO(b"Test PDF content")
        file.name = "test.pdf"
        file.content_type = "application/pdf"
        upload_file = UploadFile(file=file, filename="test.pdf")
        
        file_path, file_size = storage.save_file(upload_file, document_id=1, version_number=1)
        
        assert file_size > 0
        assert Path(file_path).exists()
        assert Path(file_path).parent.exists()
    
    def test_save_file_version_naming(self, temp_storage):
        """Test that saved file has correct version naming."""
        file = BytesIO(b"Test content")
        file.name = "test.pdf"
        file.content_type = "application/pdf"
        upload_file = UploadFile(file=file, filename="test.pdf")
        
        file_path, _ = storage.save_file(upload_file, document_id=1, version_number=2)
        
        assert "v2_" in Path(file_path).name
    
    def test_save_file_large_file_fails(self, temp_storage):
        """Test that saving large file raises error."""
        # Create file larger than max size
        large_content = b"x" * (storage.MAX_FILE_SIZE + 1)
        file = BytesIO(large_content)
        file.name = "large.pdf"
        file.content_type = "application/pdf"
        upload_file = UploadFile(file=file, filename="large.pdf")
        
        with pytest.raises(HTTPException) as exc_info:
            storage.save_file(upload_file, document_id=1, version_number=1)
        
        assert exc_info.value.status_code == 400


class TestGetFilePath:
    """Tests for get_file_path function."""
    
    def test_get_file_path_specific_version(self, temp_storage):
        """Test getting path for specific version."""
        # Create test files
        doc_path = storage.get_document_storage_path(1)
        doc_path.mkdir(parents=True, exist_ok=True)
        
        # Create version files
        (doc_path / "v1_test.pdf").touch()
        (doc_path / "v2_test.pdf").touch()
        (doc_path / "v3_test.pdf").touch()
        
        path = storage.get_file_path(document_id=1, version_number=2)
        
        assert path is not None
        assert "v2_" in path.name
    
    def test_get_file_path_latest_version(self, temp_storage):
        """Test getting path for latest version."""
        # Create test files
        doc_path = storage.get_document_storage_path(1)
        doc_path.mkdir(parents=True, exist_ok=True)
        
        # Create version files
        (doc_path / "v1_test.pdf").touch()
        (doc_path / "v2_test.pdf").touch()
        (doc_path / "v5_test.pdf").touch()  # Latest
        
        path = storage.get_file_path(document_id=1, version_number=None)
        
        assert path is not None
        assert "v5_" in path.name
    
    def test_get_file_path_nonexistent_document(self, temp_storage):
        """Test getting path for non-existent document."""
        path = storage.get_file_path(document_id=99999)
        
        assert path is None
    
    def test_get_file_path_nonexistent_version(self, temp_storage):
        """Test getting path for non-existent version."""
        # Create document directory but not the specific version
        doc_path = storage.get_document_storage_path(1)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v1_test.pdf").touch()
        
        path = storage.get_file_path(document_id=1, version_number=5)
        
        assert path is None


class TestDeleteDocumentFiles:
    """Tests for delete_document_files function."""
    
    def test_delete_document_files(self, temp_storage):
        """Test deleting all files for a document."""
        # Create document directory with files
        doc_path = storage.get_document_storage_path(1)
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "v1_test.pdf").touch()
        (doc_path / "v2_test.pdf").touch()
        
        assert doc_path.exists()
        
        storage.delete_document_files(document_id=1)
        
        assert not doc_path.exists()
    
    def test_delete_nonexistent_document_files(self, temp_storage):
        """Test deleting files for non-existent document (should not error)."""
        storage.delete_document_files(document_id=99999)
        # Should not raise exception


class TestGetFileTypeFromExtension:
    """Tests for get_file_type_from_extension function."""
    
    def test_get_file_type_pdf(self):
        """Test getting file type for PDF."""
        result = storage.get_file_type_from_extension(".pdf")
        assert result == "pdf"
    
    def test_get_file_type_docx(self):
        """Test getting file type for DOCX."""
        result = storage.get_file_type_from_extension(".docx")
        assert result == "docx"
    
    def test_get_file_type_without_dot(self):
        """Test getting file type without leading dot."""
        result = storage.get_file_type_from_extension("pdf")
        assert result == "pdf"
    
    def test_get_file_type_lowercase(self):
        """Test that file type is lowercase."""
        result = storage.get_file_type_from_extension(".PDF")
        assert result == "pdf"

