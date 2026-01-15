import os
import uuid
import shutil
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException
import mimetypes

# Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.doc'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
STORAGE_BASE = Path("storage/docs")


def get_allowed_mime_types() -> dict:
    """
    Returns dictionary of allowed MIME types.
    """
    return {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/msword': '.doc',
        'text/plain': '.txt'
    }


def validate_file(file: UploadFile) -> Tuple[str, str]:
    """
    Validates uploaded file.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Tuple of (file_extension, sanitized_filename)
        
    Raises:
        HTTPException if file is invalid
    """
    # Check if file is provided
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Get file extension
    file_ext = Path(file.filename).suffix.lower()
    
    # Validate extension
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate MIME type
    if file.content_type:
        allowed_mimes = get_allowed_mime_types()
        if file.content_type not in allowed_mimes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid MIME type. Allowed types: {', '.join(allowed_mimes.keys())}"
            )
    
    # Generate safe filename using UUID
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    
    return file_ext, safe_filename


def validate_file_size(file_size: int) -> None:
    """
    Validates file size.
    
    Args:
        file_size: Size in bytes
        
    Raises:
        HTTPException if file exceeds max size
    """
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB"
        )


def get_document_storage_path(document_id: int) -> Path:
    """
    Returns the storage path for a specific document.
    
    Args:
        document_id: Document ID
        
    Returns:
        Path object for document storage directory
    """
    doc_path = STORAGE_BASE / str(document_id)
    return doc_path


def save_file(file: UploadFile, document_id: int, version_number: int) -> Tuple[str, int]:
    """
    Saves uploaded file to storage with version naming.
    
    Args:
        file: FastAPI UploadFile object
        document_id: Document ID
        version_number: Version number (1, 2, 3, ...)
        
    Returns:
        Tuple of (file_path, file_size)
        
    Raises:
        HTTPException if file operations fail
    """
    # Validate file
    file_ext, safe_filename = validate_file(file)
    
    # Create document storage directory
    doc_path = get_document_storage_path(document_id)
    doc_path.mkdir(parents=True, exist_ok=True)
    
    # Create versioned filename
    version_filename = f"v{version_number}_{safe_filename}"
    file_path = doc_path / version_filename
    
    # Validate file size by reading content
    file_content = file.file.read()
    file_size = len(file_content)
    validate_file_size(file_size)
    
    # Reset file pointer
    file.file.seek(0)
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Return relative path as string
    relative_path = str(file_path.relative_to(Path(".")))
    return relative_path, file_size


def get_file_path(document_id: int, version_number: Optional[int] = None) -> Optional[Path]:
    """
    Gets file path for a document version.
    
    Args:
        document_id: Document ID
        version_number: Version number (None for latest)
        
    Returns:
        Path object if file exists, None otherwise
    """
    doc_path = get_document_storage_path(document_id)
    
    if not doc_path.exists():
        return None
    
    if version_number:
        # Find specific version file
        pattern = f"v{version_number}_*"
        matching_files = list(doc_path.glob(pattern))
        if matching_files:
            return matching_files[0]
    else:
        # Get latest version (highest version number)
        version_files = list(doc_path.glob("v*_*"))
        if version_files:
            # Sort by version number (extract from filename)
            version_files.sort(key=lambda x: int(x.stem.split('_')[0][1:]) if x.stem.split('_')[0][1:].isdigit() else 0, reverse=True)
            return version_files[0]
    
    return None


def delete_document_files(document_id: int) -> None:
    """
    Deletes all files for a document.
    
    Args:
        document_id: Document ID
    """
    doc_path = get_document_storage_path(document_id)
    if doc_path.exists():
        shutil.rmtree(doc_path)


def get_file_type_from_extension(extension: str) -> str:
    """
    Gets file type string from extension.
    
    Args:
        extension: File extension (e.g., '.pdf')
        
    Returns:
        File type string (e.g., 'pdf')
    """
    return extension.lstrip('.').lower()


# Initialize storage directory
STORAGE_BASE.mkdir(parents=True, exist_ok=True)

