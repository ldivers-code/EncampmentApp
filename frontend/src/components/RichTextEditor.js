import React from 'react';
import ReactQuill from 'react-quill-new';
import DOMPurify from 'dompurify';
import 'react-quill-new/dist/quill.snow.css';

const modules = {
  toolbar: [
    ['bold', 'italic', 'underline'],
    [{ 'list': 'ordered' }, { 'list': 'bullet' }],
    ['clean']
  ],
};

const formats = ['bold', 'italic', 'underline', 'list', 'bullet'];

const RichTextEditor = ({ value, onChange, placeholder, className }) => (
  <div className={`rich-text-editor ${className || ''}`} data-testid="rich-text-editor">
    <ReactQuill
      theme="snow"
      value={value || ''}
      onChange={onChange}
      modules={modules}
      formats={formats}
      placeholder={placeholder || 'Enter text...'}
    />
    <style>{`
      .rich-text-editor .ql-container { min-height: 120px; font-size: 14px; font-family: inherit; border-color: #e2e8f0; border-bottom-left-radius: 2px; border-bottom-right-radius: 2px; }
      .rich-text-editor .ql-toolbar { border-color: #e2e8f0; border-top-left-radius: 2px; border-top-right-radius: 2px; background: #f8fafc; }
      .rich-text-editor .ql-toolbar button:hover { color: #00205B; }
      .rich-text-editor .ql-toolbar button.ql-active { color: #00205B; }
      .rich-text-editor .ql-editor { padding: 12px; }
      .rich-text-editor .ql-editor ul, .rich-text-editor .ql-editor ol { padding-left: 1.5em; }
      .rich-text-editor .ql-editor p { margin-bottom: 0.25em; }
    `}</style>
  </div>
);

// Render stored HTML safely for read-only display
export const RichTextDisplay = ({ html, className }) => {
  if (!html || html === '<p><br></p>') return null;
  return (
    <div
      className={`rich-text-display prose prose-sm prose-slate max-w-none ${className || ''}`}
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }}
      data-testid="rich-text-display"
    />
  );
};

// Convert legacy plain text (with "- " bullets) to HTML
export const plainTextToHtml = (text) => {
  if (!text) return '';
  if (text.startsWith('<')) return text; // Already HTML
  const lines = text.split('\n').filter(l => l.trim());
  let html = '';
  let inList = false;
  for (const line of lines) {
    if (line.trim().startsWith('- ')) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${line.trim().substring(2)}</li>`;
    } else {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<p>${line}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
};

export default RichTextEditor;
