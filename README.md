# Knowledge Base & Document Management System

A comprehensive document management system built with FastAPI that supports document upload, version tracking, tagging, and advanced search capabilities.

## Features

✅ **Document Upload** - Upload PDF, DOCX, TXT, and DOC files  
✅ **Version Tracking** - Multiple versions per document with automatic versioning  
✅ **Metadata Storage** - Store title, description, tags, and upload information  
✅ **Tag-based Search** - Search documents by tags (single or multiple)  
✅ **Advanced Search** - Search by title, description, file type, and tags  
✅ **Safe File Storage** - Files stored with UUID-based naming and validation  
✅ **File Download** - Download specific versions of documents  

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Database (can be easily switched to PostgreSQL)
- **Python 3.8+** - Programming language

## Project Structure

```
doc_manager/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── db.py                # Database connection and setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas for validation
│   ├── crud.py              # Database operations
│   ├── storage.py           # File storage utilities
│   └── routers/
│       ├── __init__.py
│       ├── documents.py     # Document endpoints
│       └── search.py        # Search endpoints
├── storage/
│   └── docs/                # Document storage (created automatically)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation & Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at: `http://127.0.0.1:8000`

### 4. Access API Documentation

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## API Endpoints

### 1. Upload Document

**POST** `/documents/upload`

Upload a new document or add a new version to an existing document.

**Form Data:**
- `title` (required): Document title
- `description` (optional): Document description
- `tags` (optional): Comma-separated tags (e.g., "invoice,policy,hr")
- `file` (required): Document file (PDF, DOCX, TXT, DOC)
- `document_id` (optional): If provided, adds new version to existing document

**Example:**
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "title=Company Policy" \
  -F "description=HR policies and procedures" \
  -F "tags=hr,policy" \
  -F "file=@policy.pdf"
```

### 2. List Documents

**GET** `/documents`

Get list of all documents with latest version and tags.

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 100, max: 1000)

**Example:**
```bash
curl "http://127.0.0.1:8000/documents?skip=0&limit=10"
```

### 3. Search Documents

**GET** `/documents/search`

Search documents by tags, title, description, or file type.

**Query Parameters:**
- `tags` (optional): Comma-separated tags (e.g., "invoice,policy")
- `match_all` (optional): If true, document must have all tags (default: false)
- `query` (optional): Search in title and description
- `file_type` (optional): Filter by file type (pdf, docx, txt, doc)
- `skip` (optional): Pagination offset
- `limit` (optional): Maximum records to return

**Examples:**
```bash
# Search by tags
curl "http://127.0.0.1:8000/documents/search?tags=invoice,policy"

# Search by text
curl "http://127.0.0.1:8000/documents/search?query=policy"

# Advanced search
curl "http://127.0.0.1:8000/documents/search?query=policy&file_type=pdf&tags=hr"
```

### 4. Get Document Versions

**GET** `/documents/{document_id}/versions`

Get all versions of a specific document.

**Example:**
```bash
curl "http://127.0.0.1:8000/documents/1/versions"
```

### 5. Download Document

**GET** `/documents/{document_id}/download`

Download a specific version of a document.

**Query Parameters:**
- `version` (optional): Version number (defaults to latest)

**Examples:**
```bash
# Download latest version
curl "http://127.0.0.1:8000/documents/1/download" -o document.pdf

# Download specific version
curl "http://127.0.0.1:8000/documents/1/download?version=2" -o document_v2.pdf
```

## Database Schema

### Documents Table
- `id`: Primary key
- `title`: Document title
- `description`: Document description
- `created_at`: Creation timestamp

### Document Versions Table
- `id`: Primary key
- `document_id`: Foreign key to documents
- `version_number`: Version number (1, 2, 3, ...)
- `file_path`: Path to stored file
- `file_size`: File size in bytes
- `file_type`: File type (pdf, docx, txt, etc.)
- `uploaded_at`: Upload timestamp

### Tags Table
- `id`: Primary key
- `name`: Tag name (unique)

### Document Tags Table (Many-to-Many)
- `document_id`: Foreign key to documents
- `tag_id`: Foreign key to tags

## File Storage

Files are stored in the following structure:

```
storage/
└── docs/
    ├── 1/              # Document ID 1
    │   ├── v1_file.pdf
    │   └── v2_file.pdf
    └── 2/              # Document ID 2
        └── v1_file.docx
```

- Files are renamed using UUIDs for security
- Version numbers are included in filenames
- Directory traversal attacks are prevented

## Security Features

✅ **File Type Validation** - Only allowed file types (PDF, DOCX, TXT, DOC)  
✅ **File Size Limit** - Maximum 10MB per file  
✅ **Safe Filename Handling** - UUID-based filenames prevent conflicts  
✅ **MIME Type Validation** - Validates file content type  
✅ **Directory Traversal Prevention** - Prevents path manipulation attacks  

## Testing

Use the Swagger UI at `http://127.0.0.1:8000/docs` to test all endpoints interactively.

### Example Workflow

1. **Upload a document:**
   - Go to `/documents/upload` endpoint
   - Fill in title, description, tags
   - Upload a PDF file
   - Note the `document_id` returned

2. **Upload a new version:**
   - Use the same endpoint
   - Provide the `document_id` from step 1
   - Upload a new file
   - Version number will auto-increment

3. **Search documents:**
   - Use `/documents/search?tags=your_tag`
   - Or use advanced search with multiple filters

4. **Download a version:**
   - Use `/documents/{document_id}/download?version=1`

## Configuration

### File Size Limit
Default: 10MB. To change, modify `MAX_FILE_SIZE` in `app/storage.py`.

### Allowed File Types
Currently: PDF, DOCX, TXT, DOC. To modify, update `ALLOWED_EXTENSIONS` in `app/storage.py`.

### Database
Default: SQLite (`doc_manager.db`). To switch to PostgreSQL:
1. Update `SQLALCHEMY_DATABASE_URL` in `app/db.py`
2. Install `psycopg2-binary` (already in requirements.txt)

## Future Enhancements

- [ ] User authentication and authorization
- [ ] Role-based access control
- [ ] Document deletion endpoint
- [ ] Bulk document upload
- [ ] Full-text search (content indexing)
- [ ] Document preview
- [ ] Export/import functionality
- [ ] Audit logging

## License

This project is open source and available for use.

