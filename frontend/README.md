# Document Manager Frontend

React frontend for the Knowledge Base & Document Management System.

## Features

✅ **Real-time Document List** - Fetches documents from FastAPI backend  
✅ **Document Upload** - Upload PDF, DOCX, TXT, DOC files  
✅ **Search Functionality** - Search by title, description, or tags  
✅ **Version History** - View all versions of a document  
✅ **Download Documents** - Download any version  
✅ **Error Handling** - User-friendly error messages  
✅ **Loading States** - Visual feedback during operations  

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- FastAPI backend running on http://127.0.0.1:8000

## Installation

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

## Running the Application

1. **Make sure your FastAPI backend is running:**
```bash
# In the main project directory
uvicorn app.main:app --reload
```

2. **Start the React development server:**
```bash
# In the frontend directory
npm start
```

The app will open at http://localhost:3000

## Configuration

### API Base URL

If your backend runs on a different port or URL, update `API_BASE_URL` in:
```
frontend/src/services/api.js
```

Default: `http://127.0.0.1:8000`

### CORS Configuration

The FastAPI backend already has CORS enabled for all origins. If you encounter CORS issues:

1. Check that the backend is running
2. Verify the API_BASE_URL matches your backend URL
3. The backend CORS middleware is configured in `app/main.py`

## Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── App.js              # Main application component
│   ├── index.js            # React entry point
│   ├── index.css           # Global styles
│   ├── services/
│   │   └── api.js          # API service layer
│   └── utils/
│       └── formatBytes.js  # Utility functions
├── package.json            # Dependencies
└── README.md              # This file
```

## API Integration

The frontend uses the following backend endpoints:

- `GET /documents` - List all documents
- `POST /documents/upload` - Upload document
- `GET /documents/search` - Search documents
- `GET /documents/{id}/versions` - Get document versions
- `GET /documents/{id}/download` - Download document

All API calls are handled in `src/services/api.js`.

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` folder.

## Troubleshooting

**Backend Connection Error:**
- Ensure FastAPI backend is running on http://127.0.0.1:8000
- Check browser console for CORS errors
- Verify API_BASE_URL in `src/services/api.js`

**Upload Fails:**
- Check file size (max 10MB)
- Verify file type (PDF, DOCX, DOC, TXT only)
- Check backend logs for errors

**Documents Not Loading:**
- Check browser console for errors
- Verify backend is accessible
- Check network tab in browser dev tools

