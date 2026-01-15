from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from app import models, schemas
from app.storage import save_file, get_file_type_from_extension, delete_document_files
from fastapi import UploadFile, HTTPException


def get_or_create_tag(db: Session, tag_name: str) -> models.Tag:
    """
    Gets existing tag or creates new one.
    
    Args:
        db: Database session
        tag_name: Tag name
        
    Returns:
        Tag model instance
    """
    tag_name = tag_name.strip().lower()
    tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
    
    if not tag:
        tag = models.Tag(name=tag_name)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    
    return tag


def create_document(
    db: Session,
    title: str,
    description: Optional[str],
    tags_string: Optional[str],
    file: UploadFile,
    uploaded_by: Optional[str] = None
) -> schemas.DocumentUploadResponse:
    """
    Creates a new document with first version.
    
    Args:
        db: Database session
        title: Document title
        description: Document description
        tags_string: Comma-separated tags
        file: Uploaded file
        uploaded_by: User who uploaded (optional)
        
    Returns:
        DocumentUploadResponse
    """
    # Create document record
    document = models.Document(
        title=title,
        description=description
    )
    db.add(document)
    db.flush()  # Get document.id without committing
    
    # Save file (version 1)
    file_path, file_size = save_file(file, document.id, version_number=1)
    file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    file_type = get_file_type_from_extension(f".{file_ext}")
    
    # Create version record
    version = models.DocumentVersion(
        document_id=document.id,
        version_number=1,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type
    )
    db.add(version)
    
    # Process tags
    if tags_string:
        tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
        for tag_name in tag_names:
            tag = get_or_create_tag(db, tag_name)
            document.tags.append(tag)
    
    db.commit()
    db.refresh(document)
    
    return schemas.DocumentUploadResponse(
        document_id=document.id,
        version_number=1,
        message="Document uploaded successfully"
    )


def add_document_version(
    db: Session,
    document_id: int,
    file: UploadFile,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags_string: Optional[str] = None,
    uploaded_by: Optional[str] = None
) -> schemas.DocumentUploadResponse:
    """
    Adds a new version to an existing document and optionally updates metadata.
    
    Args:
        db: Database session
        document_id: Document ID
        file: Uploaded file
        title: New title (optional, updates if provided)
        description: New description (optional, updates if provided)
        tags_string: New tags (optional, replaces existing tags if provided)
        uploaded_by: User who uploaded (optional)
        
    Returns:
        DocumentUploadResponse
        
    Raises:
        HTTPException if document not found
    """
    # Get document
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update document metadata if provided
    if title:
        document.title = title
    if description is not None:  # Allow empty string to clear description
        document.description = description
    
    # Update tags if provided
    if tags_string is not None:
        # Clear existing tags
        document.tags.clear()
        # Add new tags
        if tags_string.strip():
            tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tag_names:
                tag = get_or_create_tag(db, tag_name)
                document.tags.append(tag)
    
    # Get latest version number
    latest_version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id
    ).order_by(models.DocumentVersion.version_number.desc()).first()
    
    new_version_number = (latest_version.version_number + 1) if latest_version else 1
    
    # Save file
    file_path, file_size = save_file(file, document_id, version_number=new_version_number)
    file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    file_type = get_file_type_from_extension(f".{file_ext}")
    
    # Create version record
    version = models.DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    db.refresh(document)
    
    return schemas.DocumentUploadResponse(
        document_id=document_id,
        version_number=new_version_number,
        message=f"Version {new_version_number} uploaded successfully"
    )


def get_documents(db: Session, skip: int = 0, limit: int = 100) -> List[models.Document]:
    """
    Gets list of all documents with latest version info.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Document models
    """
    return db.query(models.Document).offset(skip).limit(limit).all()


def get_document_by_id(db: Session, document_id: int) -> Optional[models.Document]:
    """
    Gets a document by ID.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        Document model or None
    """
    return db.query(models.Document).filter(models.Document.id == document_id).first()


def get_document_versions(db: Session, document_id: int) -> Optional[schemas.DocumentVersionsResponse]:
    """
    Gets all versions of a document.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        DocumentVersionsResponse or None
    """
    document = get_document_by_id(db, document_id)
    if not document:
        return None
    
    versions = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id
    ).order_by(models.DocumentVersion.version_number.asc()).all()
    
    version_responses = [
        schemas.DocumentVersionResponse.model_validate(v) for v in versions
    ]
    
    return schemas.DocumentVersionsResponse(
        document_id=document.id,
        title=document.title,
        versions=version_responses
    )


def search_documents_by_tags(
    db: Session,
    tags: List[str],
    match_all: bool = False,
    skip: int = 0,
    limit: int = 100
) -> List[models.Document]:
    """
    Searches documents by tags.
    
    Args:
        db: Database session
        tags: List of tag names to search
        match_all: If True, document must have all tags. If False, document must have any tag.
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Document models
    """
    if not tags:
        return []
    
    # Normalize tag names
    tag_names = [tag.strip().lower() for tag in tags if tag.strip()]
    
    if not tag_names:
        return []
    
    # Get tag IDs
    tag_objects = db.query(models.Tag).filter(models.Tag.name.in_(tag_names)).all()
    tag_ids = [tag.id for tag in tag_objects]
    
    if not tag_ids:
        return []
    
    if match_all:
        # Document must have all tags
        query = db.query(models.Document).join(models.document_tags).filter(
            models.document_tags.c.tag_id.in_(tag_ids)
        ).group_by(models.Document.id).having(
            db.func.count(models.document_tags.c.tag_id.distinct()) == len(tag_ids)
        )
    else:
        # Document must have any tag
        query = db.query(models.Document).join(models.document_tags).filter(
            models.document_tags.c.tag_id.in_(tag_ids)
        ).distinct()
    
    # Order by latest upload (most recent version)
    query = query.order_by(models.Document.created_at.desc())
    
    return query.offset(skip).limit(limit).all()


def search_documents_advanced(
    db: Session,
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    file_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.Document]:
    """
    Advanced search with multiple filters.
    
    Args:
        db: Database session
        query: Search query for title/description
        tags: List of tag names
        file_type: File type filter (pdf, docx, txt, etc.)
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Document models
    """
    db_query = db.query(models.Document)
    
    # Text search in title/description
    if query:
        search_term = f"%{query.lower()}%"
        db_query = db_query.filter(
            or_(
                models.Document.title.ilike(search_term),
                models.Document.description.ilike(search_term)
            )
        )
    
    # Tag filter
    if tags:
        tag_names = [tag.strip().lower() for tag in tags if tag.strip()]
        if tag_names:
            tag_objects = db.query(models.Tag).filter(models.Tag.name.in_(tag_names)).all()
            tag_ids = [tag.id for tag in tag_objects]
            if tag_ids:
                db_query = db_query.join(models.document_tags).filter(
                    models.document_tags.c.tag_id.in_(tag_ids)
                ).distinct()
    
    # File type filter (check latest version)
    if file_type:
        file_type_lower = file_type.lower().lstrip('.')
        # Get document IDs where latest version has matching file type
        # Subquery to get latest version for each document
        latest_versions = db.query(
            models.DocumentVersion.document_id,
            func.max(models.DocumentVersion.version_number).label('max_version')
        ).group_by(models.DocumentVersion.document_id).subquery()
        
        # Get document IDs with matching file type in latest version
        doc_ids_with_type = db.query(models.DocumentVersion.document_id).join(
            latest_versions,
            and_(
                models.DocumentVersion.document_id == latest_versions.c.document_id,
                models.DocumentVersion.version_number == latest_versions.c.max_version,
                models.DocumentVersion.file_type == file_type_lower
            )
        ).distinct().subquery()
        
        db_query = db_query.filter(
            models.Document.id.in_(db.query(doc_ids_with_type.c.document_id))
        )
    
    # Order by latest upload
    db_query = db_query.order_by(models.Document.created_at.desc())
    
    return db_query.offset(skip).limit(limit).all()


def delete_document(db: Session, document_id: int) -> bool:
    """
    Deletes a document and all its versions.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        True if deleted successfully
        
    Raises:
        HTTPException if document not found
    """
    # Get document
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete files from storage
    try:
        delete_document_files(document_id)
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Warning: Failed to delete files for document {document_id}: {e}")
    
    # Delete document (cascade will delete versions and tag associations)
    db.delete(document)
    db.commit()
    
    return True

