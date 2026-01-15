from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
import os

from app import crud, schemas
from app.db import get_db
from app.storage import get_file_path

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=schemas.DocumentUploadResponse)
async def upload_document(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    document_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a document or add a new version to an existing document.
    
    - **title**: Document title (required)
    - **description**: Document description (optional)
    - **tags**: Comma-separated tags (optional)
    - **file**: Document file (PDF, DOCX, TXT, DOC)
    - **document_id**: If provided, adds new version to existing document (optional)
    
    Returns document_id and version_number.
    """
    if document_id:
        # Add new version to existing document
        return crud.add_document_version(
            db=db, 
            document_id=document_id, 
            file=file,
            title=title,
            description=description,
            tags_string=tags
        )
    else:
        # Create new document
        return crud.create_document(
            db=db,
            title=title,
            description=description,
            tags_string=tags,
            file=file
        )


@router.get("", response_model=List[schemas.DocumentResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List all documents with their latest version and tags.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    documents = crud.get_documents(db=db, skip=skip, limit=limit)
    
    result = []
    for doc in documents:
        # Get latest version
        latest_version = None
        if doc.versions:
            latest = max(doc.versions, key=lambda v: v.version_number)
            latest_version = schemas.DocumentVersionResponse.model_validate(latest)
        
        # Get tags
        tags = [schemas.TagResponse.model_validate(tag) for tag in doc.tags]
        
        result.append(schemas.DocumentResponse(
            id=doc.id,
            title=doc.title,
            description=doc.description,
            created_at=doc.created_at,
            latest_version=latest_version,
            tags=tags,
            version_count=len(doc.versions)
        ))
    
    return result


@router.get("/{document_id}/versions", response_model=schemas.DocumentVersionsResponse)
def get_versions(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all versions of a specific document.
    
    - **document_id**: Document ID
    """
    versions_response = crud.get_document_versions(db=db, document_id=document_id)
    
    if not versions_response:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return versions_response


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    version: Optional[int] = Query(None, description="Version number (defaults to latest)"),
    db: Session = Depends(get_db)
):
    """
    Download a specific version of a document.
    
    - **document_id**: Document ID
    - **version**: Version number (optional, defaults to latest)
    
    Returns the file for download.
    """
    # Verify document exists
    document = crud.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get file path
    file_path = get_file_path(document_id=document_id, version_number=version)
    
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine filename for download
    if version:
        filename = f"{document.title}_v{version}{file_path.suffix}"
    else:
        # Get latest version number
        versions = crud.get_document_versions(db=db, document_id=document_id)
        if versions and versions.versions:
            latest_v = max(versions.versions, key=lambda v: v.version_number)
            filename = f"{document.title}_v{latest_v.version_number}{file_path.suffix}"
        else:
            filename = f"{document.title}{file_path.suffix}"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )


@router.get("/{document_id}/preview")
def preview_document(
    document_id: int,
    version: Optional[int] = Query(None, description="Version number (defaults to latest)"),
    db: Session = Depends(get_db)
):
    """
    Preview a specific version of a document (inline display).
    
    - **document_id**: Document ID
    - **version**: Version number (optional, defaults to latest)
    
    Returns the file for inline preview.
    """
    # Verify document exists
    document = crud.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get file path
    file_path = get_file_path(document_id=document_id, version_number=version)
    
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type based on file extension
    file_ext = file_path.suffix.lower()
    media_type_map = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain'
    }
    media_type = media_type_map.get(file_ext, 'application/octet-stream')
    
    # Determine filename
    if version:
        filename = f"{document.title}_v{version}{file_path.suffix}"
    else:
        # Get latest version number
        versions = crud.get_document_versions(db=db, document_id=document_id)
        if versions and versions.versions:
            latest_v = max(versions.versions, key=lambda v: v.version_number)
            filename = f"{document.title}_v{latest_v.version_number}{file_path.suffix}"
        else:
            filename = f"{document.title}{file_path.suffix}"
    
    # Read file content
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # Return with inline content disposition for preview
    return Response(
        content=file_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Type": media_type
        }
    )


@router.delete("/{document_id}", status_code=200)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all its versions.
    
    - **document_id**: Document ID to delete
    
    Returns success message.
    """
    crud.delete_document(db=db, document_id=document_id)
    return {"message": f"Document {document_id} deleted successfully"}

