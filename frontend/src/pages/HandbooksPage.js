import React, { useState, useEffect } from 'react';
import { getDocuments, createDocument, updateDocument, deleteDocument } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  BookOpen,
  ExternalLink,
  FileText
} from 'lucide-react';

const HandbooksPage = () => {
  const { canEdit } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    doc_type: 'handbook',
    content: '',
    file_url: ''
  });

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.filter(d => d.doc_type === 'handbook'));
    } catch (error) {
      toast.error('Failed to load handbooks');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingDoc) {
        await updateDocument(editingDoc.id, formData);
        toast.success('Handbook updated');
      } else {
        await createDocument(formData);
        toast.success('Handbook added');
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
      doc_type: 'handbook',
      content: doc.content || '',
      file_url: doc.file_url || ''
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this handbook?')) {
      try {
        await deleteDocument(id);
        toast.success('Handbook deleted');
        if (selectedDoc?.id === id) setSelectedDoc(null);
        loadDocuments();
      } catch (error) {
        toast.error('Failed to delete handbook');
      }
    }
  };

  const resetForm = () => {
    setEditingDoc(null);
    setFormData({
      title: '',
      description: '',
      doc_type: 'handbook',
      content: '',
      file_url: ''
    });
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading handbooks...</div>
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
            Handbooks
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {documents.length} handbooks available
          </p>
        </div>

        {canEdit() && (
          <Dialog open={isModalOpen} onOpenChange={(open) => {
            setIsModalOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-handbook-btn">
                <Plus className="w-4 h-4 mr-2" />
                Add Handbook
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  {editingDoc ? 'Edit Handbook' : 'Add Handbook'}
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
                    placeholder="Cadet Encampment Handbook"
                    data-testid="handbook-title-input"
                  />
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
                  <Input
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="mt-1 rounded-sm"
                    placeholder="Brief description of the handbook"
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
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Content</Label>
                  <Textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    className="mt-1 rounded-sm font-mono text-sm"
                    rows={12}
                    placeholder="Enter handbook content here..."
                  />
                </div>
                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)} className="rounded-sm">
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-handbook-btn">
                    {editingDoc ? 'Update' : 'Add'} Handbook
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Handbook List */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4">
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Available Handbooks
              </h2>
            </div>
            <div className="divide-y divide-slate-100">
              {documents.length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  <BookOpen className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No handbooks yet</p>
                </div>
              ) : (
                documents.map(doc => (
                  <div
                    key={doc.id}
                    className={`p-4 cursor-pointer hover:bg-slate-50 transition-colors ${selectedDoc?.id === doc.id ? 'bg-[#00205B]/5 border-l-4 border-[#00205B]' : ''}`}
                    onClick={() => setSelectedDoc(doc)}
                    data-testid={`handbook-item-${doc.id}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-3">
                        <BookOpen className="w-5 h-5 text-[#00205B] mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-semibold text-slate-900">{doc.title}</p>
                          {doc.description && (
                            <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">{doc.description}</p>
                          )}
                        </div>
                      </div>
                      {canEdit() && (
                        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
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
                ))
              )}
            </div>
          </div>
        </div>

        {/* Handbook Content */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-slate-200 rounded-sm">
            {selectedDoc ? (
              <>
                <div className="border-b border-slate-100 p-4 flex items-center justify-between">
                  <div>
                    <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
                      {selectedDoc.title}
                    </h2>
                    {selectedDoc.description && (
                      <p className="text-sm text-slate-500 mt-1">{selectedDoc.description}</p>
                    )}
                  </div>
                  {selectedDoc.file_url && (
                    <a
                      href={selectedDoc.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-[#00205B] hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Open Link
                    </a>
                  )}
                </div>
                <div className="p-6">
                  {selectedDoc.content ? (
                    <div className="prose prose-slate max-w-none">
                      <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 leading-relaxed">
                        {selectedDoc.content}
                      </pre>
                    </div>
                  ) : (
                    <div className="text-center text-slate-400 py-8">
                      <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>No content available</p>
                      {selectedDoc.file_url && (
                        <a
                          href={selectedDoc.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 mt-4 text-[#00205B] hover:underline"
                        >
                          <ExternalLink className="w-4 h-4" />
                          View external document
                        </a>
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-slate-400">
                <BookOpen className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg">Select a handbook to view</p>
                <p className="text-sm mt-2">Click on any handbook from the list to read its content</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HandbooksPage;
