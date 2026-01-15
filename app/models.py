from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

# Association table for many-to-many relationship between documents and tags
document_tags = Table(
    'document_tags',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class Document(Base):
    """
    Main document table - stores document identity (same across versions).
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=document_tags, back_populates="documents")


class DocumentVersion(Base):
    """
    Document versions table - each upload creates a new version record.
    """
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc.
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="versions")


class Tag(Base):
    """
    Tags table - stores unique tags.
    """
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    
    # Relationship
    documents = relationship("Document", secondary=document_tags, back_populates="tags")

