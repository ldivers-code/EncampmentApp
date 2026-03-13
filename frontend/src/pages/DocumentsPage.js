import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getDocuments, createDocument, updateDocument, deleteDocument, uploadDocumentWithFile, downloadDocumentFile } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import DocumentPreview, { canPreview } from '../components/DocumentPreview';
import {
  Plus, Edit2, Trash2, Download, FileText, File, Upload,
  Search, X, Loader2, FileSpreadsheet, Image, FileArchive,
  Presentation, FileCheck, FilePlus, Shield, Eye
} from 'lucide-react';

const DOC_TYPES = [
  { value: 'official_document', label: 'Official Document', icon: FileCheck },
  { value: 'form', label: 'Form / CAPF', icon: FilePlus },
  { value: 'reference', label: 'Reference', icon: FileText },
  { value: 'checklist', label: 'Checklist', icon: FileCheck },
  { value: 'regulation', label: 'Regulation / Policy', icon: Shield },
  { value: 'other', label: 'Other', icon: File }
];

const getFileIcon = (fileType) => {
  if (!fileType) return FileText;
  if (fileType.includes('pdf')) return FileText;
  if (fileType.includes('spreadsheet') || fileType.includes('excel') || fileType.includes('csv')) return FileSpreadsheet;
  if (fileType.includes('image')) return Image;
  if (fileType.includes('presentation') || fileType.includes('powerpoint')) return Presentation;
  if (fileType.includes('zip') || fileType.includes('archive')) return FileArchive;
  return File;
};

const formatFileSize = (bytes) => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const DocumentsPage = () => {
  const { canUploadDocuments } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [previewDoc, setPreviewDoc] = useState(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    doc_type: 'official_document',
    content: ''
  });

  const loadDocuments = useCallback(async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.filter(d => d.doc_type !== 'handbook'));
    } catch {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDocuments(); }, [loadDocuments]);

  const filteredDocs = documents.filter(doc => {
    const matchesSearch = !searchQuery ||
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.file_name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === 'all' || doc.doc_type === typeFilter;
    return matchesSearch && matchesType;
  });

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      if (!formData.title) {
        const name = e.dataTransfer.files[0].name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        setFormData(prev => ({ ...prev, title: name }));
      }
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      if (!formData.title) {
        const name = e.target.files[0].name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        setFormData(prev => ({ ...prev, title: name }));
      }
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!formData.title) { toast.error('Title is required'); return; }

    setUploading(true);
    setUploadProgress(0);

    try {
      if (selectedFile) {
        const fd = new FormData();
        fd.append('file', selectedFile);
        fd.append('title', formData.title);
        fd.append('description', formData.description);
        fd.append('doc_type', formData.doc_type);
        await uploadDocumentWithFile(fd, (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded * 100) / e.total));
        });
      } else {
        await createDocument({
          title: formData.title,
          description: formData.description,
          doc_type: formData.doc_type,
          content: formData.content
        });
      }
      toast.success('Document uploaded successfully');
      resetForm();
      setIsUploadOpen(false);
      loadDocuments();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleEdit = (doc) => {
    setEditingDoc(doc);
    setFormData({
      title: doc.title,
      description: doc.description || '',
      doc_type: doc.doc_type,
      content: doc.content || ''
    });
    setIsEditOpen(true);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      await updateDocument(editingDoc.id, {
        ...editingDoc,
        title: formData.title,
        description: formData.description,
        doc_type: formData.doc_type,
        content: formData.content
      });
      toast.success('Document updated');
      setIsEditOpen(false);
      resetForm();
      loadDocuments();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await deleteDocument(id);
      toast.success('Document deleted');
      loadDocuments();
    } catch {
      toast.error('Failed to delete');
    }
  };

  const handleDownload = async (doc) => {
    if (!doc.storage_path) {
      if (doc.file_url) window.open(doc.file_url, '_blank');
      return;
    }
    setDownloadingId(doc.id);
    try {
      const response = await downloadDocumentFile(doc.id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.file_name || 'download');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Download failed');
    } finally {
      setDownloadingId(null);
    }
  };

  const resetForm = () => {
    setEditingDoc(null);
    setSelectedFile(null);
    setFormData({ title: '', description: '', doc_type: 'official_document', content: '' });
  };

  const getDocTypeInfo = (type) => DOC_TYPES.find(t => t.value === type) || DOC_TYPES[DOC_TYPES.length - 1];

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-6 h-6 animate-spin text-[#00205B]" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Official Documents
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {filteredDocs.length} of {documents.length} documents
          </p>
        </div>
        {canUploadDocuments() && (
          <Button
            onClick={() => { resetForm(); setIsUploadOpen(true); }}
            className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
            data-testid="upload-document-btn"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Document
          </Button>
        )}
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 rounded-sm"
              data-testid="document-search"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
              </button>
            )}
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-full sm:w-48 rounded-sm" data-testid="document-type-filter">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {DOC_TYPES.map(t => (
                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Document Grid */}
      {filteredDocs.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <FileText className="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <p className="text-lg text-slate-500 font-medium">
            {documents.length === 0 ? 'No documents yet' : 'No matching documents'}
          </p>
          <p className="text-sm text-slate-400 mt-2">
            {documents.length === 0 ? 'Upload your first document to get started' : 'Try adjusting your search or filters'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredDocs.map(doc => {
            const FileIcon = doc.storage_path ? getFileIcon(doc.file_type) : getDocTypeInfo(doc.doc_type).icon;
            return (
              <div
                key={doc.id}
                className="bg-white border border-slate-200 rounded-sm hover:border-[#00205B]/30 hover:shadow-sm transition-all group"
                data-testid={`document-card-${doc.id}`}
              >
                <div className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2.5 bg-[#00205B]/5 rounded-sm flex-shrink-0">
                      <FileIcon className="w-5 h-5 text-[#00205B]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-900 truncate" title={doc.title}>{doc.title}</h3>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm bg-slate-100 text-slate-600 border border-slate-200">
                          {getDocTypeInfo(doc.doc_type).label}
                        </span>
                        {doc.file_name && (
                          <span className="text-[10px] text-slate-400 truncate max-w-[120px]" title={doc.file_name}>
                            {doc.file_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {doc.description && (
                    <p className="mt-3 text-sm text-slate-500 line-clamp-2">{doc.description}</p>
                  )}

                  {doc.file_size > 0 && (
                    <p className="mt-2 text-xs text-slate-400">{formatFileSize(doc.file_size)}</p>
                  )}

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {(doc.storage_path || doc.content) && canPreview(doc.file_type) && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPreviewDoc(doc)}
                          className="h-8 text-xs rounded-sm"
                          data-testid={`preview-document-${doc.id}`}
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          Preview
                        </Button>
                      )}
                      {(doc.storage_path || doc.file_url) && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(doc)}
                          disabled={downloadingId === doc.id}
                          className="h-8 text-xs rounded-sm"
                          data-testid={`download-document-${doc.id}`}
                        >
                          {downloadingId === doc.id ? (
                            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3 mr-1" />
                          )}
                          Download
                        </Button>
                      )}
                      {!doc.storage_path && !doc.file_url && doc.content && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPreviewDoc(doc)}
                          className="h-8 text-xs rounded-sm"
                          data-testid={`view-document-${doc.id}`}
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          View
                        </Button>
                      )}
                    </div>
                    {canUploadDocuments() && (
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(doc)} className="h-7 w-7 p-0">
                          <Edit2 className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => handleDelete(doc.id)}
                          className="h-7 w-7 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload Modal */}
      <Dialog open={isUploadOpen} onOpenChange={(open) => { setIsUploadOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Upload Document
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpload} className="space-y-4 mt-2">
            {/* Drag-and-drop zone */}
            <div
              className={`border-2 border-dashed rounded-sm p-6 text-center transition-colors cursor-pointer
                ${dragActive ? 'border-[#00205B] bg-[#00205B]/5' : 'border-slate-300 hover:border-slate-400'}
                ${selectedFile ? 'bg-green-50 border-green-300' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              data-testid="document-dropzone"
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                data-testid="document-file-input"
              />
              {selectedFile ? (
                <div className="flex items-center justify-center gap-3">
                  <File className="w-8 h-8 text-green-600" />
                  <div className="text-left">
                    <p className="font-medium text-slate-900 text-sm">{selectedFile.name}</p>
                    <p className="text-xs text-slate-500">{formatFileSize(selectedFile.size)}</p>
                  </div>
                  <button type="button" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }} className="ml-2">
                    <X className="w-4 h-4 text-slate-400 hover:text-red-500" />
                  </button>
                </div>
              ) : (
                <>
                  <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                  <p className="text-sm text-slate-600 font-medium">Drop a file here or click to browse</p>
                  <p className="text-xs text-slate-400 mt-1">Any file type supported</p>
                </>
              )}
            </div>

            {uploading && (
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div className="bg-[#00205B] h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
              </div>
            )}

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData(p => ({ ...p, title: e.target.value }))}
                required
                className="mt-1 rounded-sm"
                placeholder="e.g. CAPF 60-80 Application"
                data-testid="document-title-input"
              />
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Document Type</Label>
              <Select value={formData.doc_type} onValueChange={(v) => setFormData(p => ({ ...p, doc_type: v }))}>
                <SelectTrigger className="mt-1 rounded-sm" data-testid="document-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DOC_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData(p => ({ ...p, description: e.target.value }))}
                className="mt-1 rounded-sm"
                placeholder="Brief description"
              />
            </div>

            {!selectedFile && (
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Content (if no file)</Label>
                <Textarea
                  value={formData.content}
                  onChange={(e) => setFormData(p => ({ ...p, content: e.target.value }))}
                  className="mt-1 rounded-sm text-sm"
                  rows={6}
                  placeholder="Enter text content..."
                />
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsUploadOpen(false)} className="rounded-sm">
                Cancel
              </Button>
              <Button type="submit" disabled={uploading} className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="submit-document-btn">
                {uploading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Uploading...</> : 'Upload'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditOpen} onOpenChange={(open) => { setIsEditOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Edit Document
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSubmit} className="space-y-4 mt-2">
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData(p => ({ ...p, title: e.target.value }))}
                required
                className="mt-1 rounded-sm"
                data-testid="edit-document-title"
              />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Document Type</Label>
              <Select value={formData.doc_type} onValueChange={(v) => setFormData(p => ({ ...p, doc_type: v }))}>
                <SelectTrigger className="mt-1 rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DOC_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData(p => ({ ...p, description: e.target.value }))}
                className="mt-1 rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Content</Label>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData(p => ({ ...p, content: e.target.value }))}
                className="mt-1 rounded-sm text-sm"
                rows={6}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsEditOpen(false)} className="rounded-sm">Cancel</Button>
              <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-edit-document-btn">Save Changes</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Preview Modal */}
      <DocumentPreview
        doc={previewDoc}
        open={!!previewDoc}
        onClose={() => setPreviewDoc(null)}
        onDownload={handleDownload}
      />
    </div>
  );
};

export default DocumentsPage;
