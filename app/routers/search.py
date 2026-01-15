from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app import crud, schemas
from app.db import get_db

router = APIRouter(prefix="/documents", tags=["search"])


@router.get("/search", response_model=schemas.SearchResponse)
def search_documents(
    tags: Optional[str] = Query(None, description="Comma-separated tags (e.g., 'invoice,policy')"),
    match_all: bool = Query(False, description="If True, document must have all tags"),
    query: Optional[str] = Query(None, description="Search in title and description"),
    file_type: Optional[str] = Query(None, description="Filter by file type (pdf, docx, txt, etc.)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Search documents with multiple filters.
    
    - **tags**: Comma-separated tags to search (e.g., 'invoice,policy')
    - **match_all**: If True, document must have all specified tags
    - **query**: Search term for title and description
    - **file_type**: Filter by file type (pdf, docx, txt, doc)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    
    Examples:
    - Search by tags: `/documents/search?tags=invoice,policy`
    - Search by text: `/documents/search?query=policy`
    - Advanced search: `/documents/search?query=policy&file_type=pdf&tags=hr`
    """
    # Parse tags
    tag_list = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Determine search method
    if tag_list and not query and not file_type:
        # Simple tag search
        documents = crud.search_documents_by_tags(
            db=db,
            tags=tag_list,
            match_all=match_all,
            skip=skip,
            limit=limit
        )
    else:
        # Advanced search
        documents = crud.search_documents_advanced(
            db=db,
            query=query,
            tags=tag_list,
            file_type=file_type,
            skip=skip,
            limit=limit
        )
    
    # Format response
    result = []
    for doc in documents:
        # Get latest version
        latest_version = None
        if doc.versions:
            latest = max(doc.versions, key=lambda v: v.version_number)
            latest_version = schemas.DocumentVersionResponse.model_validate(latest)
        
        # Get tags
        tag_responses = [schemas.TagResponse.model_validate(tag) for tag in doc.tags]
        
        result.append(schemas.DocumentResponse(
            id=doc.id,
            title=doc.title,
            description=doc.description,
            created_at=doc.created_at,
            latest_version=latest_version,
            tags=tag_responses,
            version_count=len(doc.versions)
        ))
    
    return schemas.SearchResponse(
        documents=result,
        total=len(result)
    )

