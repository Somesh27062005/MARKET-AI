import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Upload, 
  Trash2, 
  FileText, 
  Sparkles,
  CheckCircle,
  HelpCircle,
  AlertTriangle
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';

export default function KnowledgeBase({ getCsrfToken }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchDocs = async () => {
    try {
      const res = await fetch('/api/knowledge');
      if (res.ok) {
        const data = await res.json();
        setDocs(Array.isArray(data) ? data : (data.documents || []));
      }
    } catch (err) {
      console.error("Knowledge base fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError('');
      setSuccess('');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload first.');
      return;
    }
    setError('');
    setSuccess('');
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/knowledge', {
        method: 'POST',
        headers: {
          'X-CSRF-Token': getCsrfToken()
        },
        body: formData
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setSuccess(`Document "${file.filename || file.name}" uploaded and parsed successfully!`);
        setFile(null);
        // Clear input value
        document.getElementById('file-upload-input').value = '';
        fetchDocs();
      } else {
        setError(data.error || 'Failed to upload document.');
      }
    } catch (err) {
      console.error(err);
      setError('Network communication failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to remove this document? This will remove its context from future AI generations.')) return;
    try {
      const res = await fetch(`/api/knowledge/${docId}`, {
        method: 'DELETE',
        headers: {
          'X-CSRF-Token': getCsrfToken()
        }
      });

      if (res.ok) {
        fetchDocs();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Knowledge Base & Context</h1>
        <p className="text-gray-400 mt-1">Upload company profiles, product specifications, and target briefings to ground your AI generations.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Upload Panel */}
        <GlassCard className="lg:col-span-1 border border-white/5 space-y-6">
          <div className="flex items-center space-x-2 border-b border-white/5 pb-3">
            <Upload className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Upload Context File</h2>
          </div>

          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed border-white/10 hover:border-indigo-500/30 rounded-2xl p-6 text-center cursor-pointer transition-all bg-white/2 hover:bg-white/5 relative">
              <input
                id="file-upload-input"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <FileText className="w-10 h-10 text-gray-500 mx-auto mb-2" />
              <p className="text-xs font-semibold text-white">
                {file ? file.name : 'Select or drop a file'}
              </p>
              <p className="text-[10px] text-gray-500 mt-1">Supports PDF, Docx, or Plain Text up to 10MB</p>
            </div>

            {error && (
              <p className="text-xs text-rose-400 font-medium bg-rose-500/10 border border-rose-500/10 rounded-xl p-3">
                {error}
              </p>
            )}

            {success && (
              <p className="text-xs text-emerald-400 font-medium bg-emerald-500/10 border border-emerald-500/10 rounded-xl p-3">
                {success}
              </p>
            )}

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full glass-button-primary flex items-center justify-center space-x-2 py-2.5 disabled:opacity-40"
            >
              {uploading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>Parse & Ground File</span>
                </>
              )}
            </button>
          </form>

          {/* Explanation box */}
          <div className="text-[11px] text-gray-500 border-t border-white/5 pt-4 space-y-2 leading-relaxed">
            <h4 className="font-semibold text-white flex items-center space-x-1">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>How grounding works</span>
            </h4>
            <p>
              Uploaded documents are read on the backend using Python text-extractors. This text is cached and appended to all prompt workflows (campaigns, sales pitches, SWOT analyses, roadmaps) as a grounding framework. This ensures the LLaMA model understands your specific corporate terminology, product advantages, and target objectives.
            </p>
          </div>
        </GlassCard>

        {/* Documents list */}
        <div className="lg:col-span-2 space-y-6">
          <GlassCard className="border border-white/5">
            <div className="flex items-center space-x-2 border-b border-white/5 pb-3 mb-6">
              <Database className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Grounded Documents Repository</h2>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : docs.length === 0 ? (
              <div className="text-center py-12 text-gray-500 space-y-2">
                <FileText className="w-10 h-10 text-gray-600 mx-auto" />
                <h4 className="font-semibold text-white">No custom documents uploaded</h4>
                <p className="text-xs">Your AI Advisor is running on general industry defaults. Upload details to personalize outputs.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {docs.map((doc) => (
                  <div key={doc.id} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs flex justify-between items-center group">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/10 flex items-center justify-center text-indigo-400 font-bold shrink-0">
                        DOC
                      </div>
                      <div>
                        <h4 className="font-bold text-white group-hover:text-indigo-400 transition-colors">{doc.filename}</h4>
                        <span className="text-[10px] text-gray-500 block mt-0.5">Uploaded {new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all"
                      title="Remove document context"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
