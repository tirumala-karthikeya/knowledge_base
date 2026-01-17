import pytest
import tempfile
import shutil
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from io import BytesIO
from typing import Generator

from app.db import Base, get_db
from app.main import app
from app import models


# Test database setup - use temporary file database for reliability
_test_db_file = None

def get_test_db_url():
    """Get test database URL, creating temp file if needed."""
    global _test_db_file
    if _test_db_file is None:
        fd, _test_db_file = tempfile.mkstemp(suffix='.db')
        os.close(fd)  # Close file descriptor, we'll use the path
    return f"sqlite:///{_test_db_file}"

test_engine = create_engine(
    get_test_db_url(),
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """
    Create a fresh database session for each test.
    Creates tables, yields session, then drops tables.
    """
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=test_engine)
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Clean up: drop tables and recreate for next test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """
    Create a test client with database override.
    """
    # Ensure tables are created (db_session fixture already does this)
    # But we need to ensure they're committed/visible
    Base.metadata.create_all(bind=test_engine)
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def temp_storage() -> Generator:
    """
    Create a temporary storage directory for each test.
    """
    temp_dir = tempfile.mkdtemp()
    
    # Monkey patch storage path
    import app.storage
    original_base = app.storage.STORAGE_BASE
    app.storage.STORAGE_BASE = Path(temp_dir) / "docs"
    app.storage.STORAGE_BASE.mkdir(parents=True, exist_ok=True)
    
    # Also update the get_document_storage_path function's reference
    # by ensuring it uses the patched STORAGE_BASE
    yield Path(temp_dir)
    
    # Restore original
    app.storage.STORAGE_BASE = original_base
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf_file():
    """
    Create a mock PDF file for testing.
    """
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    file = BytesIO(content)
    file.name = "test_document.pdf"
    file.content_type = "application/pdf"
    return file


@pytest.fixture
def sample_txt_file():
    """
    Create a mock TXT file for testing.
    """
    content = b"This is a test text file content."
    file = BytesIO(content)
    file.name = "test_document.txt"
    file.content_type = "text/plain"
    return file


@pytest.fixture
def sample_docx_file():
    """
    Create a mock DOCX file for testing.
    """
    # Minimal DOCX structure (ZIP with XML)
    content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00testdocx[Content_Types].xml"
    file = BytesIO(content)
    file.name = "test_document.docx"
    file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return file


@pytest.fixture
def upload_file_pdf(sample_pdf_file):
    """
    Create an UploadFile object for PDF.
    """
    from fastapi import UploadFile
    sample_pdf_file.seek(0)
    return UploadFile(file=sample_pdf_file, filename="test_document.pdf")


@pytest.fixture
def upload_file_txt(sample_txt_file):
    """
    Create an UploadFile object for TXT.
    """
    from fastapi import UploadFile
    sample_txt_file.seek(0)
    return UploadFile(file=sample_txt_file, filename="test_document.txt")


@pytest.fixture
def upload_file_docx(sample_docx_file):
    """
    Create an UploadFile object for DOCX.
    """
    from fastapi import UploadFile
    sample_docx_file.seek(0)
    return UploadFile(file=sample_docx_file, filename="test_document.docx")


@pytest.fixture
def sample_document(db_session):
    """
    Create a sample document in the database for testing.
    """
    document = models.Document(
        title="Test Document",
        description="This is a test document"
    )
    db_session.add(document)
    db_session.flush()
    
    version = models.DocumentVersion(
        document_id=document.id,
        version_number=1,
        file_path="storage/docs/1/v1_test.pdf",
        file_size=1024,
        file_type="pdf"
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(document)
    
    return document


@pytest.fixture
def sample_document_with_tags(db_session):
    """
    Create a sample document with tags in the database.
    """
    # Create tags
    tag1 = models.Tag(name="invoice")
    tag2 = models.Tag(name="policy")
    db_session.add(tag1)
    db_session.add(tag2)
    db_session.flush()
    
    # Create document
    document = models.Document(
        title="Invoice Policy",
        description="Policy document about invoices"
    )
    document.tags.append(tag1)
    document.tags.append(tag2)
    db_session.add(document)
    db_session.flush()
    
    version = models.DocumentVersion(
        document_id=document.id,
        version_number=1,
        file_path="storage/docs/1/v1_test.pdf",
        file_size=2048,
        file_type="pdf"
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(document)
    
    return document


@pytest.fixture
def sample_document_multiple_versions(db_session):
    """
    Create a document with multiple versions.
    """
    document = models.Document(
        title="Multi-Version Document",
        description="Document with multiple versions"
    )
    db_session.add(document)
    db_session.flush()
    
    # Create 3 versions
    for v in range(1, 4):
        version = models.DocumentVersion(
            document_id=document.id,
            version_number=v,
            file_path=f"storage/docs/{document.id}/v{v}_test.pdf",
            file_size=1024 * v,
            file_type="pdf"
        )
        db_session.add(version)
    
    db_session.commit()
    db_session.refresh(document)
    
    return document

