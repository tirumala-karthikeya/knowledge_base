import React, { useState, useEffect, useMemo } from 'react';
import { getDocuments, uploadDocument, searchDocuments, getDocumentVersions, downloadDocument, deleteDocument } from './services/api';
import { formatBytes } from './utils/formatBytes';

const App = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState('list'); // 'list' or 'upload'
  const [selectedDoc, setSelectedDoc] = useState(null); // For version viewing
  const [versions, setVersions] = useState(null); // Cached versions for selected doc
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadMode, setUploadMode] = useState('new'); // 'new' or 'version'
  const [selectedDocForVersion, setSelectedDocForVersion] = useState(null);
  const [previewDoc, setPreviewDoc] = useState(null); // Document for preview

  // Fetch documents on component mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Fetch documents from API
  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDocuments();
      setDocuments(data);
    } catch (err) {
      setError('Failed to load documents. Make sure the backend is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch versions when a document is selected
  useEffect(() => {
    if (selectedDoc) {
      fetchVersions(selectedDoc.id);
    }
  }, [selectedDoc]);

  // Fetch document versions
  const fetchVersions = async (documentId) => {
    try {
      const data = await getDocumentVersions(documentId);
      setVersions(data);
    } catch (err) {
      console.error('Error fetching versions:', err);
      setVersions(null);
    }
  };

  // Search documents
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchDocuments();
      return;
    }

    try {
      setLoading(true);
      setError(null);
      // Search by query (searches title and description)
      const data = await searchDocuments({ query: searchQuery });
      setDocuments(data.documents || []);
    } catch (err) {
      setError('Failed to search documents.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Handle search on Enter key
  const handleSearchKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // Filtering Logic (client-side fallback if search API fails)
  const filteredDocs = useMemo(() => {
    if (!searchQuery.trim()) {
      return documents;
    }
    return documents.filter(doc => 
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.description && doc.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      doc.tags.some(tag => tag.name.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [documents, searchQuery]);

  // Handle document upload
  const handleUpload = async (e) => {
    e.preventDefault();
    setUploading(true);
    setUploadError(null);

    const formData = new FormData(e.target);
    const file = formData.get('file');
    
    if (!file || file.size === 0) {
      setUploadError('Please select a file to upload.');
      setUploading(false);
      return;
    }

    // Check file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size exceeds 10MB limit.');
      setUploading(false);
      return;
    }

    // If uploading new version, add document_id and validate
    if (uploadMode === 'version') {
      if (!selectedDocForVersion) {
        setUploadError('Please select a document to update.');
        setUploading(false);
        return;
      }
      formData.append('document_id', selectedDocForVersion.id);
      // Title is required for version uploads too
      if (!formData.get('title') || formData.get('title').trim() === '') {
        setUploadError('Title is required.');
        setUploading(false);
        return;
      }
    }

    try {
      await uploadDocument(formData);
      // Reset form
      e.target.reset();
      setSelectedDocForVersion(null);
      setUploadMode('new');
      // Refresh documents list
      await fetchDocuments();
      // Switch to list view
      setView('list');
      setUploadError(null);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to upload document. Please try again.';
      setUploadError(errorMessage);
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  // Handle download
  const handleDownload = async (documentId, version = null) => {
    try {
      await downloadDocument(documentId, version);
    } catch (err) {
      alert('Failed to download document. Please try again.');
      console.error('Download error:', err);
    }
  };

  // Handle version modal open
  const handleViewVersions = async (doc) => {
    setSelectedDoc(doc);
  };

  // Handle delete
  const handleDelete = async (documentId, title) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"?\n\nThis will delete the document and all its versions. This action cannot be undone.`)) {
      return;
    }

    try {
      await deleteDocument(documentId);
      // Refresh documents list
      await fetchDocuments();
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to delete document. Please try again.';
      alert(errorMessage);
      console.error('Delete error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans selection:bg-gray-200">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <h1 className="text-lg font-semibold tracking-tight uppercase">Knowledge Base</h1>
            <div className="hidden md:flex gap-6">
              <button 
                onClick={() => {
                  setView('list');
                  setSearchQuery('');
                  fetchDocuments();
                }}
                className={`text-sm font-medium transition-colors ${view === 'list' ? 'text-black' : 'text-gray-400 hover:text-gray-600'}`}
              >
                All Documents
              </button>
              <button 
                onClick={() => setView('upload')}
                className={`text-sm font-medium transition-colors ${view === 'upload' ? 'text-black' : 'text-gray-400 hover:text-gray-600'}`}
              >
                Upload New
              </button>
            </div>
          </div>
          <div className="flex-1 max-w-xs ml-8 hidden sm:block">
            <input 
              type="text" 
              placeholder="Search by title, tag, or description..."
              className="w-full bg-gray-100 border-none rounded-md px-4 py-2 text-sm focus:ring-2 focus:ring-gray-200 outline-none transition-all"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleSearchKeyPress}
            />
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {view === 'list' ? (
          <section>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Library</h2>
                <p className="text-gray-500 text-sm mt-1">
                  {loading ? 'Loading...' : `Managing ${documents.length} internal records`}
                </p>
              </div>
              <button 
                onClick={() => setView('upload')}
                className="bg-black text-white px-5 py-2.5 rounded-md text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                Add Document
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
                <button 
                  onClick={fetchDocuments}
                  className="ml-4 underline font-semibold"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Loading State */}
            {loading && documents.length === 0 ? (
              <div className="text-center py-24">
                <p className="text-gray-400 text-sm">Loading documents...</p>
              </div>
            ) : filteredDocs.length > 0 ? (
              <div className="grid gap-4">
                {filteredDocs.map(doc => (
                  <div 
                    key={doc.id} 
                    onClick={(e) => {
                      // Only open preview if clicking on the card itself, not buttons
                      if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
                        if (doc.latest_version && doc.latest_version.file_type === 'pdf') {
                          setPreviewDoc(doc);
                        }
                      }
                    }}
                    className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-sm transition-all group flex flex-col md:flex-row md:items-center justify-between gap-6 cursor-pointer"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-lg font-semibold leading-none">{doc.title}</h3>
                        {doc.latest_version && (
                          <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded uppercase font-bold">
                            {doc.latest_version.file_type}
                          </span>
                        )}
                      </div>
                      {doc.description && (
                        <p className="text-gray-500 text-sm mb-4 line-clamp-1">{doc.description}</p>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {doc.tags && doc.tags.length > 0 ? (
                          doc.tags.map(tag => (
                            <span key={tag.id} className="text-[11px] border border-gray-200 px-2 py-0.5 rounded text-gray-600 lowercase">
                              #{tag.name}
                            </span>
                          ))
                        ) : (
                          <span className="text-[11px] text-gray-400 italic">No tags</span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-start md:items-end gap-1 border-t md:border-t-0 pt-4 md:pt-0 border-gray-100">
                      {doc.latest_version && (
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span>v{doc.latest_version.version_number}</span>
                          <span>•</span>
                          <span>{formatBytes(doc.latest_version.file_size)}</span>
                        </div>
                      )}
                      <div className="flex gap-3 mt-2 flex-wrap" onClick={(e) => e.stopPropagation()}>
                        {doc.latest_version && (
                          <button 
                            onClick={() => handleDownload(doc.id)}
                            className="text-sm font-semibold border-b border-transparent hover:border-black transition-all"
                          >
                            Download
                          </button>
                        )}
                        <button 
                          onClick={() => handleViewVersions(doc)}
                          className="text-sm font-semibold border-b border-transparent hover:border-black transition-all"
                        >
                          View History
                        </button>
                        <button 
                          onClick={() => {
                            setUploadMode('version');
                            setSelectedDocForVersion(doc);
                            setView('upload');
                          }}
                          className="text-sm font-semibold text-blue-600 border-b border-transparent hover:border-blue-600 transition-all"
                        >
                          Update pdf
                        </button>
                        <button 
                          onClick={() => handleDelete(doc.id, doc.title)}
                          className="text-sm font-semibold text-red-600 border-b border-transparent hover:border-red-600 transition-all"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-24 border-2 border-dashed border-gray-200 rounded-xl">
                <p className="text-gray-400 text-sm">
                  {searchQuery ? 'No documents found matching your search.' : 'No documents yet. Upload your first document!'}
                </p>
              </div>
            )}
          </section>
        ) : (
          <section className="max-w-2xl mx-auto">
            <div className="mb-8">
              <button 
                onClick={() => {
                  setView('list');
                  setUploadError(null);
                }}
                className="text-gray-400 hover:text-black text-sm font-medium mb-4 flex items-center gap-2"
              >
                ← Back to Library
              </button>
              <h2 className="text-2xl font-bold tracking-tight">Upload Document</h2>
              <p className="text-gray-500 text-sm mt-1">Files are securely stored and versioned.</p>
            </div>

            {/* Upload Error */}
            {uploadError && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {uploadError}
              </div>
            )}

            <form onSubmit={handleUpload} className="bg-white border border-gray-200 rounded-xl p-8 space-y-6">
              {/* Upload Mode Selection */}
              <div className="pb-6 border-b border-gray-200">
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">Upload Type</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="uploadMode"
                      value="new"
                      checked={uploadMode === 'new'}
                      onChange={(e) => {
                        setUploadMode('new');
                        setSelectedDocForVersion(null);
                      }}
                      className="w-4 h-4 text-black focus:ring-black"
                    />
                    <span className="text-sm font-medium">New Document</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="uploadMode"
                      value="version"
                      checked={uploadMode === 'version'}
                      onChange={(e) => setUploadMode('version')}
                      className="w-4 h-4 text-black focus:ring-black"
                    />
                    <span className="text-sm font-medium">Update pdf</span>
                  </label>
                </div>
              </div>

              {/* Document Selector for Version Upload */}
              {uploadMode === 'version' && (
                <div className="pb-4 border-b border-gray-100">
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
                    Select Document to Update *
                  </label>
                  <select
                    value={selectedDocForVersion?.id || ''}
                    onChange={(e) => {
                      const docId = parseInt(e.target.value);
                      const doc = documents.find(d => d.id === docId);
                      setSelectedDocForVersion(doc || null);
                    }}
                    required={uploadMode === 'version'}
                    className="w-full border-b border-gray-200 py-2 focus:border-black outline-none transition-colors bg-transparent"
                  >
                    <option value="">-- Select a document --</option>
                    {documents.map(doc => (
                      <option key={doc.id} value={doc.id}>
                        {doc.title} {doc.latest_version ? `(v${doc.latest_version.version_number})` : ''}
                      </option>
                    ))}
                  </select>
                  {selectedDocForVersion && (
                    <p className="text-xs text-gray-500 mt-2">
                      Current version: v{selectedDocForVersion.latest_version?.version_number || 1} • 
                      Next version will be: v{(selectedDocForVersion.latest_version?.version_number || 0) + 1}
                    </p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Title *</label>
                <input 
                  name="title"
                  required
                  type="text" 
                  placeholder="e.g. Sales Strategy 2024"
                  className="w-full border-b border-gray-200 py-2 focus:border-black outline-none transition-colors"
                />
              </div>
              
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Description</label>
                <textarea 
                  name="description"
                  rows="3"
                  placeholder="Provide a brief summary of the document contents..."
                  className="w-full border-b border-gray-200 py-2 focus:border-black outline-none transition-colors resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Tags</label>
                  <input 
                    name="tags"
                    type="text" 
                    placeholder="legal, internal, draft"
                    className="w-full border-b border-gray-200 py-2 focus:border-black outline-none transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">File *</label>
                  <input 
                    name="file"
                    required
                    type="file" 
                    accept=".pdf,.docx,.doc,.txt"
                    className="w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100 cursor-pointer"
                  />
                  <p className="text-xs text-gray-400 mt-1">PDF, DOCX, DOC, TXT (max 10MB)</p>
                </div>
              </div>

              <div className="pt-4">
                <button 
                  type="submit"
                  disabled={uploading}
                  className="w-full bg-black text-white py-4 rounded-lg font-semibold hover:bg-gray-800 transition-all shadow-lg shadow-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? 'Uploading...' : 'Confirm Upload'}
                </button>
              </div>
            </form>
          </section>
        )}
      </main>

      {/* PDF Preview Modal */}
      {previewDoc && (
        <div 
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6"
          onClick={() => setPreviewDoc(null)}
        >
          <div 
            className="bg-white w-full max-w-5xl h-[90vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">{previewDoc.title}</h2>
                <p className="text-gray-400 text-sm">
                  Version {previewDoc.latest_version?.version_number || 1} • {previewDoc.latest_version?.file_type.toUpperCase()}
                </p>
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={() => handleDownload(previewDoc.id)}
                  className="bg-black text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
                >
                  Download
                </button>
                <button 
                  onClick={() => setPreviewDoc(null)}
                  className="text-gray-400 hover:text-black transition-colors text-2xl"
                >
                  &times;
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-hidden bg-gray-100">
              {previewDoc.latest_version?.file_type === 'pdf' ? (
                <iframe
                  src={`http://127.0.0.1:8000/documents/${previewDoc.id}/preview`}
                  className="w-full h-full border-0"
                  title={`Preview of ${previewDoc.title}`}
                  type="application/pdf"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <p>Preview not available for {previewDoc.latest_version?.file_type.toUpperCase()} files. Please download to view.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {selectedDoc && (
        <div 
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6"
          onClick={() => {
            setSelectedDoc(null);
            setVersions(null);
          }}
        >
          <div 
            className="bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-8 border-b border-gray-100 flex justify-between items-start">
              <div>
                <h2 className="text-xl font-bold">{selectedDoc.title}</h2>
                <p className="text-gray-400 text-sm">Version History</p>
              </div>
              <button 
                onClick={() => {
                  setSelectedDoc(null);
                  setVersions(null);
                }}
                className="text-gray-400 hover:text-black transition-colors text-2xl"
              >
                &times;
              </button>
            </div>

            <div className="p-8 max-h-96 overflow-y-auto">
              {versions && versions.versions ? (
                <div className="space-y-4">
                  {versions.versions.map((version) => (
                    <div 
                      key={version.id} 
                      className="flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center text-xs font-bold">
                          v{version.version_number}
                        </div>
                        <div>
                          <p className="text-sm font-semibold">Version {version.version_number}</p>
                          <p className="text-[11px] text-gray-400 uppercase font-medium">
                            {new Date(version.uploaded_at).toLocaleDateString()} • {formatBytes(version.file_size)}
                          </p>
                        </div>
                      </div>
                      <button 
                        onClick={() => handleDownload(selectedDoc.id, version.version_number)}
                        className="text-xs font-bold uppercase tracking-tighter hover:underline"
                      >
                        Download
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-400 text-sm">Loading versions...</p>
                </div>
              )}
            </div>

            <div className="p-8 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
              <button 
                onClick={() => {
                  if (window.confirm(`Are you sure you want to delete "${selectedDoc.title}"?\n\nThis will delete the document and all its versions. This action cannot be undone.`)) {
                    handleDelete(selectedDoc.id, selectedDoc.title).then(() => {
                      setSelectedDoc(null);
                      setVersions(null);
                    });
                  }
                }}
                className="bg-red-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
              >
                Delete Document
              </button>
              <button 
                onClick={() => {
                  setSelectedDoc(null);
                  setVersions(null);
                }}
                className="bg-black text-white px-6 py-2 rounded-lg text-sm font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;

