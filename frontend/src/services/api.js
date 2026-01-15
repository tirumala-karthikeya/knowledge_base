import axios from 'axios';

// Base URL for API - adjust if your backend runs on different port
const API_BASE_URL = 'http://127.0.0.1:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Document API Service
 * All functions to interact with FastAPI backend
 */

/**
 * Get all documents
 */
export const getDocuments = async (skip = 0, limit = 100) => {
  try {
    const response = await api.get('/documents', {
      params: { skip, limit },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching documents:', error);
    throw error;
  }
};

/**
 * Upload a new document or add version to existing document
 */
export const uploadDocument = async (formData) => {
  try {
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading document:', error);
    throw error;
  }
};

/**
 * Search documents
 */
export const searchDocuments = async (params) => {
  try {
    const response = await api.get('/documents/search', {
      params,
    });
    return response.data;
  } catch (error) {
    console.error('Error searching documents:', error);
    throw error;
  }
};

/**
 * Get all versions of a document
 */
export const getDocumentVersions = async (documentId) => {
  try {
    const response = await api.get(`/documents/${documentId}/versions`);
    return response.data;
  } catch (error) {
    console.error('Error fetching document versions:', error);
    throw error;
  }
};

/**
 * Download a document version
 */
export const downloadDocument = async (documentId, version = null) => {
  try {
    const params = version ? { version } : {};
    const response = await api.get(`/documents/${documentId}/download`, {
      params,
      responseType: 'blob', // Important for file downloads
    });
    
    // Create blob URL and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    
    // Try to get filename from response headers
    const contentDisposition = response.headers['content-disposition'];
    let filename = `document_${documentId}${version ? `_v${version}` : ''}.pdf`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    
    return true;
  } catch (error) {
    console.error('Error downloading document:', error);
    throw error;
  }
};

/**
 * Delete a document
 */
export const deleteDocument = async (documentId) => {
  try {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting document:', error);
    throw error;
  }
};

export default api;

