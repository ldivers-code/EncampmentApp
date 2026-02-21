import React, { useState, useEffect } from 'react';
import { getDocuments, createDocument, updateDocument, deleteDocument } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  FileText,
  ExternalLink,
  Download,
  File,
  FileCheck,
  FilePlus
} from 'lucide-react';

const DocumentsPage = () => {
  const { canEdit } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [typeFilter, setTypeFilter] = useState('all');

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    doc_type: 'official_document',
    content: '',
    file_url: ''
  });

  const docTypes = [
    { value: 'official_document', label: 'Official Document', icon: FileCheck },
    { value: 'form', label: 'Form', icon: FilePlus }
  ];

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.filter(d => d.doc_type !== 'handbook'));
    } catch (error) {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const filteredDocuments = typeFilter === 'all' 
    ? documents 
    : documents.filter(d => d.doc_type === typeFilter);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingDoc) {
        await updateDocument(editingDoc.id, formData);
        toast.success('Document updated');
      } else {
        await createDocument(formData);
        toast.success('Document added');
      }
      setIsModalOpen(false);
      resetForm();
      loadDocuments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEdit = (doc) => {
    setEditingDoc(doc);
    setFormData({
      title: doc.title,
      description: doc.description || '',
      doc_type: doc.doc_type,
      content: doc.content || '',
      file_url: doc.file_url || ''
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await deleteDocument(id);
        toast.success('Document deleted');
        loadDocuments();
      } catch (error) {
        toast.error('Failed to delete document');
      }
    }
  };

  const resetForm = () => {
    setEditingDoc(null);
    setFormData({
      title: '',
      description: '',
      doc_type: 'official_document',
      content: '',
      file_url: ''
    });
  };

  const getDocIcon = (type) => {
    const docType = docTypes.find(t => t.value === type);
    return docType?.icon || File;
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading documents...</div>
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
            {documents.length} documents available
          </p>
        </div>

        {canEdit() && (
          <Dialog open={isModalOpen} onOpenChange={(open) => {
            setIsModalOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-document-btn">
                <Plus className="w-4 h-4 mr-2" />
                Add Document
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  {editingDoc ? 'Edit Document' : 'Add Document'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                  <Input
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    required
                    className="mt-1 rounded-sm"
                    placeholder="CAPF 60-80 Application"
                    data-testid="document-title-input"
                  />
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Document Type</Label>
                  <Select
                    value={formData.doc_type}
                    onValueChange={(value) => setFormData({ ...formData, doc_type: value })}
                  >
                    <SelectTrigger className="mt-1 rounded-sm" data-testid="document-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {docTypes.map(type => (
                        <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
                  <Input
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="mt-1 rounded-sm"
                    placeholder="Brief description of the document"
                  />
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">External Link (Optional)</Label>
                  <Input
                    type="url"
                    value={formData.file_url}
                    onChange={(e) => setFormData({ ...formData, file_url: e.target.value })}
                    className="mt-1 rounded-sm"
                    placeholder="https://..."
                  />
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Content (Optional)</Label>
                  <Textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    className="mt-1 rounded-sm font-mono text-sm"
                    rows={8}
                    placeholder="Enter document content or notes here..."
                  />
                </div>
                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)} className="rounded-sm">
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-document-btn">
                    {editingDoc ? 'Update' : 'Add'} Document
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Filter */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6">
        <div className="flex items-center gap-4">
          <span className="text-xs uppercase tracking-wide text-slate-500">Filter:</span>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-48 rounded-sm" data-testid="document-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Documents</SelectItem>
              {docTypes.map(type => (
                <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Documents Grid */}
      {filteredDocuments.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <FileText className="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <p className="text-slate-400">No documents available</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocuments.map(doc => {
            const DocIcon = getDocIcon(doc.doc_type);
            return (
              <div 
                key={doc.id} 
                className="bg-white border border-slate-200 rounded-sm hover:border-[#00205B]/30 transition-colors"
                data-testid={`document-card-${doc.id}`}
              >
                <div className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-[#00205B]/10 rounded-sm">
                      <DocIcon className="w-5 h-5 text-[#00205B]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-900 truncate">{doc.title}</h3>
                      <span className="inline-block mt-1 px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm bg-slate-100 text-slate-600 border border-slate-200">
                        {doc.doc_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                  
                  {doc.description && (
                    <p className="mt-3 text-sm text-slate-500 line-clamp-2">{doc.description}</p>
                  )}

                  <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {doc.file_url && (
                        <a
                          href={doc.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-[#00205B] hover:underline"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Open
                        </a>
                      )}
                    </div>
                    
                    {canEdit() && (
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(doc)}
                          className="h-7 w-7 p-0"
                        >
                          <Edit2 className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(doc.id)}
                          className="h-7 w-7 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                        >
                          <Trash2 className="w-3 h-3" />
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
    </div>
  );
};

export default DocumentsPage;
