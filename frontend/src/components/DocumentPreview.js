import React, { useState, useEffect, useCallback } from 'react';
import { previewDocumentFile } from '../services/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { X, Download, Loader2, FileText, Eye, Maximize2 } from 'lucide-react';
import { toast } from 'sonner';

const PREVIEWABLE_TYPES = {
  'application/pdf': 'pdf',
  'image/jpeg': 'image',
  'image/png': 'image',
  'image/gif': 'image',
  'image/webp': 'image',
  'image/svg+xml': 'image',
  'text/plain': 'text',
  'text/csv': 'text',
  'text/html': 'text',
  'text/markdown': 'text',
  'application/json': 'text',
  'text/xml': 'text',
  'application/xml': 'text',
};

export const canPreview = (fileType) => {
  if (!fileType) return false;
  if (PREVIEWABLE_TYPES[fileType]) return true;
  if (fileType.startsWith('image/')) return true;
  if (fileType.startsWith('text/')) return true;
  return false;
};

export const getPreviewType = (fileType) => {
  if (!fileType) return null;
  if (PREVIEWABLE_TYPES[fileType]) return PREVIEWABLE_TYPES[fileType];
  if (fileType.startsWith('image/')) return 'image';
  if (fileType.startsWith('text/')) return 'text';
  return null;
};

const DocumentPreview = ({ doc, open, onClose, onDownload }) => {
  const [blobUrl, setBlobUrl] = useState(null);
  const [textContent, setTextContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const previewType = getPreviewType(doc?.file_type);

  const loadPreview = useCallback(async () => {
    // If doc has content but no storage_path, show content directly (no loading needed)
    if (!doc?.storage_path && doc?.content) {
      setLoading(false);
      return;
    }
    
    if (!doc?.id || !doc?.storage_path || !open) return;

    setLoading(true);
    setError(null);
    setBlobUrl(null);
    setTextContent(null);

    try {
      const response = await previewDocumentFile(doc.id);
      const blob = new Blob([response.data], { type: doc.file_type });

      if (previewType === 'text') {
        const text = await blob.text();
        setTextContent(text);
      } else {
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
      }
    } catch {
      setError('Failed to load preview');
      toast.error('Failed to load file preview');
    } finally {
      setLoading(false);
    }
  }, [doc?.id, doc?.storage_path, doc?.file_type, previewType, open]);

  useEffect(() => {
    loadPreview();
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [loadPreview]);

  if (!doc || !open) return null;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="max-w-5xl w-[95vw] h-[90vh] flex flex-col p-0 gap-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <Eye className="w-4 h-4 text-[#00205B] flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-900 truncate text-sm">{doc.title}</h3>
              {doc.file_name && (
                <p className="text-xs text-slate-500 truncate">{doc.file_name}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {onDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDownload(doc)}
                className="h-8 text-xs rounded-sm"
                data-testid="preview-download-btn"
              >
                <Download className="w-3 h-3 mr-1" />
                Download
              </Button>
            )}
          </div>
        </div>

        {/* Preview Content */}
        <div className="flex-1 overflow-auto bg-slate-100">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-[#00205B] mx-auto mb-3" />
                <p className="text-sm text-slate-500">Loading preview...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-500">{error}</p>
                {onDownload && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDownload(doc)}
                    className="mt-3 rounded-sm"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Download instead
                  </Button>
                )}
              </div>
            </div>
          ) : previewType === 'pdf' && blobUrl ? (
            <iframe
              src={blobUrl}
              className="w-full h-full border-0"
              title={`Preview: ${doc.title}`}
              data-testid="pdf-preview-frame"
            />
          ) : previewType === 'image' && blobUrl ? (
            <div className="flex items-center justify-center h-full p-6">
              <img
                src={blobUrl}
                alt={doc.title}
                className="max-w-full max-h-full object-contain rounded shadow-lg"
                data-testid="image-preview"
              />
            </div>
          ) : previewType === 'text' && textContent !== null ? (
            <div className="p-6">
              <pre
                className="bg-white border border-slate-200 rounded-sm p-4 text-sm text-slate-700 font-mono whitespace-pre-wrap overflow-auto max-h-[calc(90vh-120px)]"
                data-testid="text-preview"
              >
                {textContent}
              </pre>
            </div>
          ) : doc.content ? (
            <div className="p-6">
              <pre className="bg-white border border-slate-200 rounded-sm p-4 text-sm text-slate-700 font-sans whitespace-pre-wrap">
                {doc.content}
              </pre>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-500">Preview not available for this file type</p>
                {onDownload && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDownload(doc)}
                    className="mt-3 rounded-sm"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Download to view
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DocumentPreview;
