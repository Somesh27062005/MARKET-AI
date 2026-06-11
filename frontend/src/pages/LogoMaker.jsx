import React, { useState, useEffect } from 'react';
import { Palette, Sparkles, Loader2, Download, Image as ImageIcon, Trash2, Calendar } from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';

export default function LogoMaker({ getCsrfToken }) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [image, setImage] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);

  const suggestions = [
    'A minimalist tech company icon, sleek blue and silver tones',
    'Organic coffee shop badge with a coffee branch, warm earthly tones',
    'Cyberpunk gaming brand logo, neon purple and teal glow',
    'Abstract geometric emblem for a sustainable green energy platform'
  ];

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/v2/logo-maker/history');
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setHistory(data.history || []);
        }
      }
    } catch (err) {
      console.error("Failed to fetch logo history:", err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setError('');
    setImage(null);

    try {
      const response = await fetch('/api/v2/logo-maker', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ prompt: prompt.trim() })
      });

      const data = await response.json();
      if (response.ok && data.success) {
        setImage(data.image);
        fetchHistory(); // Refresh DB history list automatically
      } else {
        setError(data.error || 'Failed to generate logo. Please try again.');
      }
    } catch (err) {
      console.error(err);
      setError('A network error occurred. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteHistory = async (id, e) => {
    e.stopPropagation(); // Prevent loading item details
    try {
      const response = await fetch(`/api/v2/logo-maker/history/${id}`, {
        method: 'DELETE',
        headers: {
          'X-CSRF-Token': getCsrfToken()
        }
      });
      if (response.ok) {
        setHistory(prev => prev.filter(item => item.id !== id));
      }
    } catch (err) {
      console.error("Failed to delete history record:", err);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide flex items-center space-x-3">
          <Palette className="w-8 h-8 text-indigo-400" />
          <span>Logo Maker AI</span>
        </h1>
        <p className="text-gray-400 mt-1">
          Instantly generate professional brand logos using state-of-the-art AI generation models.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Controls Card */}
        <div className="lg:col-span-3 space-y-6">
          <GlassCard className="border border-white/10 shadow-2xl relative" interactive={false}>
            <form onSubmit={handleGenerate} className="space-y-6">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Describe Your Logo Concept
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g., A minimalist logo for a software startup featuring a clean mountain shape, geometric design, dark theme..."
                  rows={4}
                  className="w-full glass-input bg-surface-900/60 resize-none font-sans text-sm"
                  required
                  disabled={loading}
                />
              </div>

              {/* Suggestions */}
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Quick Ideas / Samples
                </label>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setPrompt(suggestion)}
                      className="text-[11px] text-gray-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 hover:border-indigo-500/20 py-1.5 px-3 rounded-xl transition-all font-medium text-left cursor-pointer"
                      disabled={loading}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !prompt.trim()}
                className="w-full glass-button-primary flex items-center justify-center space-x-2 py-3 disabled:opacity-50 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                    <span>Creating Brand Logo...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5 text-white animate-pulse" />
                    <span>Generate Logo</span>
                  </>
                )}
              </button>
            </form>
          </GlassCard>

          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-4 text-xs text-rose-400 font-medium">
              {error}
            </div>
          )}
        </div>

        {/* Preview Panel Card */}
        <div className="lg:col-span-2">
          <GlassCard className="border border-white/10 shadow-2xl h-full min-h-[380px] flex flex-col items-center justify-center p-6 text-center relative overflow-hidden" interactive={false}>
            {loading ? (
              <div className="space-y-4">
                <div className="w-16 h-16 rounded-full bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mx-auto relative">
                  <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                </div>
                <p className="text-sm font-medium text-gray-300">Rendering visual elements...</p>
                <p className="text-xs text-gray-500 max-w-xs">AI is designing colors, shapes and composition.</p>
              </div>
            ) : image ? (
              <div className="space-y-6 w-full flex flex-col items-center">
                <div className="relative group rounded-2xl overflow-hidden border border-white/15 shadow-xl bg-surface-900/40 p-2">
                  <img
                    src={image}
                    alt="Generated Logo"
                    className="w-64 h-64 object-cover rounded-xl shadow-inner transition-transform duration-500 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-xl">
                    <ImageIcon className="w-8 h-8 text-white" />
                  </div>
                </div>

                <div className="flex space-x-3 w-full">
                  <a
                    href={image}
                    download="marketmind_generated_logo.jpg"
                    className="flex-1 glass-button-primary flex items-center justify-center space-x-2 text-sm py-2.5 cursor-pointer"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Logo</span>
                  </a>
                </div>
              </div>
            ) : (
              <div className="space-y-4 py-8">
                <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto text-gray-500 mb-2">
                  <ImageIcon className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Logo Preview</h3>
                <p className="text-xs text-gray-400 max-w-xs mx-auto">
                  Your generated logo will appear here. Enter a concept on the left and trigger generation.
                </p>
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* Generation History */}
      <GlassCard className="border border-white/10 shadow-2xl p-6" interactive={false}>
        <div className="flex items-center space-x-2 border-b border-white/5 pb-3 mb-6">
          <ImageIcon className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Logo Design History</h2>
        </div>

        {history.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-xs">
            No design history available. Your generated logos will be saved here automatically.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6">
            {history.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  setPrompt(item.prompt);
                  setImage(item.image_data);
                  setError('');
                }}
                className="group relative cursor-pointer rounded-2xl overflow-hidden border border-white/5 bg-white/2 hover:bg-white/5 hover:border-indigo-500/20 p-2.5 transition-all hover:scale-[1.03]"
              >
                <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-surface-900/40">
                  <img
                    src={item.image_data}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                  {/* Delete overlay button */}
                  <button
                    onClick={(e) => handleDeleteHistory(item.id, e)}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-600 text-rose-400 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity z-10 cursor-pointer"
                    title="Delete Design"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                
                <div className="mt-2.5 space-y-1">
                  <p className="text-[10px] text-gray-400 font-medium truncate max-w-full" title={item.prompt}>
                    {item.prompt}
                  </p>
                  <p className="text-[8px] text-gray-500 flex items-center space-x-1">
                    <Calendar className="w-2.5 h-2.5" />
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
