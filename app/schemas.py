from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TagResponse(TagBase):
    id: int

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    id: int
    version_number: int
    file_path: str
    file_size: int
    file_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[str] = Field(None, description="Comma-separated tags")


class DocumentUpload(DocumentBase):
    pass


class DocumentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    latest_version: Optional[DocumentVersionResponse] = None
    tags: List[TagResponse] = []
    version_count: int = 0

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    document_id: int
    version_number: int
    message: str


class DocumentVersionsResponse(BaseModel):
    document_id: int
    title: str
    versions: List[DocumentVersionResponse]

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

