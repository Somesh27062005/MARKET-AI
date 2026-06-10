import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  Send, 
  Sparkles, 
  Download, 
  Share2, 
  CheckCircle, 
  HelpCircle,
  TrendingUp,
  Percent,
  Eye,
  Calendar,
  Layers,
  FileText,
  MessageSquare
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';
import ChatAssistant from '../components/ChatAssistant.jsx';

export default function CampaignGenerator({ getCsrfToken }) {
  const ALL_PLATFORMS = ['LinkedIn', 'Twitter/X', 'Facebook', 'WhatsApp'];
  const [product, setProduct] = useState('');
  const [audience, setAudience] = useState('');
  const [platform, setPlatform] = useState('LinkedIn, Twitter/X, Facebook, WhatsApp');
  const [goals, setGoals] = useState('');
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState('');
  const [suggesting, setSuggesting] = useState(false);
  const [postingStates, setPostingStates] = useState({});
  const [toast, setToast] = useState(null);
  const location = useLocation();

  useEffect(() => {
    if (location.state?.loadReportId) {
      const reportId = location.state.loadReportId;
      window.history.replaceState({}, document.title);
      
      const loadReport = async () => {
        setLoading(true);
        setError('');
        try {
          const res = await fetch(`/api/v2/reports/${reportId}`);
          if (res.ok) {
            const data = await res.json();
            if (data.success && data.report) {
              const r = data.report;
              if (r.input_dict) {
                if (r.input_dict.product !== undefined) setProduct(r.input_dict.product || '');
                if (r.input_dict.audience !== undefined) setAudience(r.input_dict.audience || '');
                if (r.input_dict.platform !== undefined) setPlatform(r.input_dict.platform || '');
                if (r.input_dict.goals !== undefined) setGoals(r.input_dict.goals || '');
                if (r.input_dict.budget !== undefined) setBudget(r.input_dict.budget || '');
              }
              if (r.result_dict) {
                setResult(r.result_dict);
              }
            } else {
              setError(data.error || 'Failed to load report.');
            }
          } else {
            setError('Failed to fetch report from server.');
          }
        } catch (err) {
          console.error(err);
          setError('Error loading report.');
        } finally {
          setLoading(false);
        }
      };
      loadReport();
    }
  }, [location.state]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const copyToClipboard = async (text) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (err) {
        console.error("Failed to copy using navigator.clipboard", err);
      }
    }
    // Fallback using temporary textarea
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);
      return successful;
    } catch (err) {
      console.error("Fallback copy failed", err);
      return false;
    }
  };

  const executePostPublish = async (idx, platform, copy) => {
    setPostingStates(prev => ({ ...prev, [idx]: 'posting' }));
    const minDelay = new Promise(resolve => setTimeout(resolve, 1000));
    try {
      const apiCall = fetch('/api/v2/campaign/post', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          platform: platform,
          copy: copy
        })
      });
      const [res] = await Promise.all([apiCall, minDelay]);
      const data = await res.json();
      if (res.ok && data.success) {
        setPostingStates(prev => ({ ...prev, [idx]: 'success' }));
        
        // Reset the button back to clickable state after 3.5 seconds
        setTimeout(() => {
          setPostingStates(prev => ({ ...prev, [idx]: 'idle' }));
        }, 3500);

        // Fail-safe copy to clipboard for all posts using robust fallback
        await copyToClipboard(copy);
        
        const cleanPlatform = platform.toLowerCase();
        if (cleanPlatform.includes('twitter') || cleanPlatform === 'x') {
          // Twitter/X supports url pre-fill cleanly
          const tweetUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(copy)}`;
          window.open(tweetUrl, '_blank');
          showToast("Twitter compose opened! Post copy synced to clipboard as backup.");
        } else if (cleanPlatform.includes('whatsapp')) {
          // WhatsApp supports url pre-fill cleanly
          const waUrl = `https://web.whatsapp.com/send?text=${encodeURIComponent(copy)}`;
          window.open(waUrl, '_blank');
          showToast("WhatsApp Web opened! Text pre-filled.");
        } else if (cleanPlatform.includes('linkedin')) {
          // Use clipboard copy + new tab redirect to LinkedIn feed composer to bypass URL parsing truncation bugs
          showToast("Full post copied! Opening LinkedIn feed composer (press Ctrl+V to paste)...", "success");
          window.open('https://www.linkedin.com/feed/?shareActive=true', '_blank');
        } else if (cleanPlatform.includes('facebook')) {
          showToast("Full post copied! Opening Facebook (press Ctrl+V to paste)...", "success");
          window.open('https://www.facebook.com/', '_blank');
        } else {
          showToast("Post content copied to clipboard!");
        }
      } else {
        setPostingStates(prev => ({ ...prev, [idx]: 'error' }));
        setTimeout(() => {
          setPostingStates(prev => ({ ...prev, [idx]: 'idle' }));
        }, 3000);
        alert(data.error || `Failed to post to ${platform}`);
      }
    } catch (err) {
      console.error(err);
      setPostingStates(prev => ({ ...prev, [idx]: 'error' }));
      setTimeout(() => {
        setPostingStates(prev => ({ ...prev, [idx]: 'idle' }));
      }, 3000);
      alert('Network error during posting simulation.');
    }
  };

  const handlePublishPost = async (idx, post) => {
    let normPlatform = post.platform || "LinkedIn";
    if (normPlatform.toLowerCase().includes("linkedin")) normPlatform = "LinkedIn";
    else if (normPlatform.toLowerCase().includes("twitter") || normPlatform.toLowerCase().includes("x")) normPlatform = "Twitter/X";
    else if (normPlatform.toLowerCase().includes("facebook")) normPlatform = "Facebook";
    else if (normPlatform.toLowerCase().includes("whatsapp")) normPlatform = "WhatsApp";
    await executePostPublish(idx, normPlatform, post.copy);
  };

  const handleSuggestInputs = async () => {
    setSuggesting(true);
    setError('');
    try {
      const res = await fetch('/api/v2/suggest_inputs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ module: 'campaign' })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.success && data.suggestions) {
          const s = data.suggestions;
          setProduct(s.product || '');
          setAudience(s.audience || '');
          
          let suggestedPlat = s.platform || '';
          if (suggestedPlat) {
            const parts = suggestedPlat.split(',').map(p => p.trim());
            const filtered = parts.filter(p => {
              return ALL_PLATFORMS.some(valid => valid.toLowerCase() === p.toLowerCase() || p.toLowerCase().includes(valid.toLowerCase()));
            }).map(p => {
              return ALL_PLATFORMS.find(valid => valid.toLowerCase() === p.toLowerCase() || p.toLowerCase().includes(valid.toLowerCase()));
            });
            const uniqueFiltered = [...new Set(filtered)];
            if (uniqueFiltered.length > 0) {
              setPlatform(uniqueFiltered.join(', '));
            } else {
              setPlatform('LinkedIn, Twitter/X, Facebook, WhatsApp');
            }
          } else {
            setPlatform('LinkedIn, Twitter/X, Facebook, WhatsApp');
          }
          
          setGoals(s.goals || '');
          setBudget(s.budget || '');
        } else {
          setError(data.error || 'Failed to retrieve suggestions.');
        }
      } else {
        setError(data.error || 'Failed to connect to assistant.');
      }
    } catch (err) {
      console.error(err);
      setError('Communication error when fetching suggestions.');
    } finally {
      setSuggesting(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!product || !audience) {
      setError('Please fill in both the Product and Target Audience fields.');
      return;
    }
    setError('');
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch('/api/v2/campaign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ product, audience, platform, goals, budget })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setResult(data.data);
      } else {
        setError(data.error || 'Failed to generate campaign. Please verify Groq API key.');
      }
    } catch (err) {
      console.error(err);
      setError('Network communication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!result) return;
    try {
      const res = await fetch('/api/v2/export/pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          module: 'campaign',
          title: result.campaign_name || 'Campaign Strategy Report',
          data: result
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `marketmind_campaign_${product.replace(/\s+/g, '_').toLowerCase()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        alert('PDF Generation failed.');
      }
    } catch (err) {
      console.error(err);
      alert('Error exporting PDF.');
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">AI Campaign Generator</h1>
        <p className="text-gray-400 mt-1">Develop complete platform-specific campaigns based on real business context.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Configuration panel */}
        <GlassCard className="lg:col-span-1 border border-white/5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-6">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Campaign configuration</h2>
            </div>
            <button
              type="button"
              onClick={handleSuggestInputs}
              disabled={suggesting}
              className="text-[10px] font-bold bg-indigo-600 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-lg border border-indigo-500/25 flex items-center space-x-1 transition-all disabled:opacity-40 shadow-sm"
              title="Auto-fill form inputs based on your company context & uploaded knowledge base documents"
            >
              {suggesting ? (
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Sparkles className="w-3 h-3" />
                  <span>Suggest</span>
                </>
              )}
            </button>
          </div>

          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Product or Service Name</label>
              <input
                type="text"
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                placeholder="e.g. Enterprise Cloud Analytics"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Target Buyer Audience</label>
              <textarea
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                placeholder="e.g. Chief Operations Officers at Fortune 500 retail companies"
                rows="3"
                className="w-full glass-input"
              ></textarea>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Campaign Platforms</label>
              <div className="grid grid-cols-2 gap-2 bg-white/2 p-3 rounded-xl border border-white/5">
                {ALL_PLATFORMS.map((plat) => {
                  const selected = platform.split(',').map(p => p.trim()).filter(Boolean);
                  const isChecked = selected.includes(plat);
                  return (
                    <label key={plat} className="flex items-center space-x-2 text-xs text-gray-300 cursor-pointer select-none py-1 hover:text-white transition-all">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {
                          if (isChecked) {
                            if (selected.length > 1) {
                              setPlatform(selected.filter(p => p !== plat).join(', '));
                            } else {
                              showToast("Please select at least one platform", "error");
                            }
                          } else {
                            setPlatform([...selected, plat].join(', '));
                          }
                        }}
                        className="rounded border-white/10 bg-slate-900 text-indigo-600 focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5"
                      />
                      <span>{plat}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Core Marketing Objective</label>
              <input
                type="text"
                value={goals}
                onChange={(e) => setGoals(e.target.value)}
                placeholder="e.g. Demo registrations, sales calls"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Budget Target (Monthly)</label>
              <select
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="w-full glass-input"
              >
                <option value="under $1k">Under $1,000</option>
                <option value="$1k-$5k">$1,000 – $5,000</option>
                <option value="$5k-$25k">$5,000 – $25,000</option>
                <option value="$25k-$100k">$25,000 – $100,000</option>
                <option value="$100k+">$100,000+</option>
              </select>
            </div>

            {error && (
              <p className="text-xs text-rose-400 font-medium bg-rose-500/10 border border-rose-500/10 rounded-xl p-3">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full glass-button-primary flex items-center justify-center space-x-2 py-2.5 disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Generate Campaign</span>
                </>
              )}
            </button>
          </form>
        </GlassCard>

        {/* Results Screen */}
        <div className="lg:col-span-2">
          {loading && (
            <GlassCard className="h-96 flex flex-col items-center justify-center space-y-4 border border-white/5 bg-surface-800/20">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white">Generating Strategic Campaign Plan</h3>
                <p className="text-xs text-gray-500 mt-1">AI Agent orchestrator runs multi-layered prompt flows...</p>
              </div>
            </GlassCard>
          )}

          {!loading && !result && (
            <GlassCard className="h-96 flex flex-col items-center justify-center text-center space-y-4 border border-white/5">
              <HelpCircle className="w-12 h-12 text-gray-600" />
              <div>
                <h3 className="text-lg font-semibold text-white">No active campaign generated</h3>
                <p className="text-xs text-gray-500 mt-1">Fill out the configuration parameters on the left to begin.</p>
              </div>
            </GlassCard>
          )}

          {!loading && result && (
            <div className="space-y-6">
              {/* Top summary card */}
              <GlassCard className="border border-indigo-500/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 flex items-center space-x-2">
                  <button 
                    onClick={handleExportPDF}
                    className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl border border-white/5 transition-all flex items-center space-x-1.5 text-xs font-semibold"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export PDF</span>
                  </button>
                </div>

                <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-bold">Marketing campaign</span>
                <h2 className="text-2xl font-display font-extrabold text-white mt-1">
                  {result.campaign_name || 'AI Marketing Campaign'}
                </h2>

                {/* Metrics highlights */}
                <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-white/5">
                  <div className="text-center bg-white/2 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Est. Reach</span>
                    <span className="text-lg font-bold text-white mt-1 block">{result.estimated_reach || 'N/A'}</span>
                  </div>
                  <div className="text-center bg-white/2 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Est. CTR</span>
                    <span className="text-lg font-bold text-cyan-400 mt-1 block">{result.estimated_ctr || 'N/A'}</span>
                  </div>
                  <div className="text-center bg-white/2 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Est. CVR</span>
                    <span className="text-lg font-bold text-emerald-400 mt-1 block">{result.estimated_cvr || 'N/A'}</span>
                  </div>
                </div>
              </GlassCard>

              {/* Navigation Tabs */}
              <div className="flex border-b border-white/5 text-sm flex-wrap">
                {[
                  { id: 'overview', label: 'Overview', icon: FileText },
                  { id: 'audience', label: 'Persona Profile', icon: Eye },
                  { id: 'funnel', label: 'Funnel tactics', icon: Layers },
                  { id: 'content', label: 'Ads & Copy', icon: Send },
                  { id: 'social_posts', label: 'Social Posts', icon: Share2 },
                  { id: 'calendar', label: 'Schedule', icon: Calendar }
                ].map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center space-x-2 pb-3 px-4 border-b-2 font-semibold transition-all ${activeTab === tab.id ? 'border-indigo-500 text-white' : 'border-transparent text-gray-400 hover:text-white'}`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Tab Contents */}
              <div className="min-h-96">
                {/* 1. OVERVIEW */}
                {activeTab === 'overview' && (
                  <GlassCard className="space-y-6">
                    <div>
                      <h3 className="text-base font-bold text-white mb-2">Executive Overview</h3>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {result.executive_campaign_overview || result.campaign_name}
                      </p>
                    </div>

                    <div>
                      <h3 className="text-base font-bold text-white mb-3">Core Strategic Objectives</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {Array.isArray(result.strategic_goals) && result.strategic_goals.length > 0 ? (
                          result.strategic_goals.map((goal, idx) => (
                            <div key={idx} className="bg-white/2 p-4 rounded-xl border border-white/5 space-y-2">
                              <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                                <span className="w-5 h-5 rounded-full bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-xs font-bold">{idx+1}</span>
                                <span>{typeof goal === 'object' && goal !== null ? (goal.goal_name || '') : goal}</span>
                              </h4>
                              {goal.business_context && <p className="text-xs text-gray-400">{goal.business_context}</p>}
                            </div>
                          ))
                        ) : (
                          (Array.isArray(result.objectives) ? result.objectives : []).map((obj, idx) => (
                            <div key={idx} className="bg-white/2 p-4 rounded-xl border border-white/5 flex items-center space-x-3 text-sm text-gray-300">
                              <CheckCircle className="w-5 h-5 text-indigo-400 shrink-0" />
                              <span>{typeof obj === 'object' && obj !== null ? (obj.objective || obj.title || JSON.stringify(obj)) : obj}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </GlassCard>
                )}

                {/* 2. PERSONA PROFILE */}
                {activeTab === 'audience' && (
                  <GlassCard className="space-y-6">
                    <div>
                      <h3 className="text-base font-bold text-white mb-2">Primary Target Persona</h3>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {result.persona_profile?.business_challenges || result.persona?.role || 'Custom buyer persona generated for campaign.'}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-white/5">
                      <div>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Key Pain Points</h4>
                        <ul className="space-y-2 text-xs text-gray-300">
                          {(result.persona_profile?.pain_points || result.persona?.pain_points || []).map((pt, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5"></span>
                              <span>{typeof pt === 'object' && pt !== null ? JSON.stringify(pt) : pt}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Buying Motivations</h4>
                        <ul className="space-y-2 text-xs text-gray-300">
                          {(result.persona_profile?.buying_motivations || result.persona?.goals || []).map((gl, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5"></span>
                              <span>{typeof gl === 'object' && gl !== null ? JSON.stringify(gl) : gl}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </GlassCard>
                )}

                {/* 3. FUNNEL TACTICS */}
                {activeTab === 'funnel' && (
                  <div className="space-y-4">
                    {['awareness', 'consideration', 'conversion'].map((stage) => {
                      const stageData = result.funnel?.[stage] || {};
                      const colorsMap = {
                        awareness: 'indigo',
                        consideration: 'cyan',
                        conversion: 'emerald'
                      };
                      const color = colorsMap[stage] || 'indigo';

                      return (
                        <GlassCard key={stage} className="border border-white/5">
                          <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                            <h4 className="text-sm font-bold text-white capitalize">{stage} stage</h4>
                            <span className="text-xs text-gray-400 font-semibold bg-white/5 py-1 px-2.5 rounded-lg">
                              Budget Allocation: {stageData.budget_pct || 33}%
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                            <div>
                              <h5 className="font-bold text-gray-400 uppercase tracking-wider mb-2">Tactics / Channels</h5>
                              <div className="flex flex-wrap gap-1.5">
                                {(stageData.tactics || []).map((tac, i) => (
                                  <span key={i} className="bg-white/5 px-2 py-1 rounded text-white font-medium">
                                    {typeof tac === 'object' && tac !== null ? JSON.stringify(tac) : tac}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <div>
                              <h5 className="font-bold text-gray-400 uppercase tracking-wider mb-2">Metrics monitored</h5>
                              <ul className="space-y-1 text-gray-300">
                                {(stageData.kpis || []).map((kp, i) => (
                                  <li key={i} className="flex items-center space-x-1.5">
                                    <span className="w-1 h-1 rounded-full bg-white/20"></span>
                                    <span>{typeof kp === 'object' && kp !== null ? JSON.stringify(kp) : kp}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </GlassCard>
                      );
                    })}
                  </div>
                )}

                {/* 4. ADS & COPY */}
                {activeTab === 'content' && (
                  <div className="space-y-6">
                    {/* Content Ideas */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-4">Content Ideas</h3>
                      <div className="space-y-3">
                        {(result.content_ideas || []).map((idea, i) => {
                          const ideaTitle = typeof idea === 'object' ? idea.headline || idea.title : `Idea #${i+1}`;
                          const ideaDesc = typeof idea === 'object' ? idea.description || idea.content : idea;
                          return (
                            <div key={i} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs">
                              <h4 className="font-bold text-white">{ideaTitle}</h4>
                              <p className="text-gray-400 mt-1">{ideaDesc}</p>
                            </div>
                          );
                        })}
                      </div>
                    </GlassCard>

                    {/* Ad Copies */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-4">Ad Copy Variations</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {(result.ad_copies || []).map((ad, i) => (
                          <div key={i} className="bg-white/2 p-4 rounded-xl border border-white/5 flex flex-col justify-between space-y-4">
                            <div>
                              <div className="flex items-center justify-between text-[10px] text-gray-500 font-bold uppercase mb-2">
                                <span>Variant #{i+1}</span>
                                <span className="text-indigo-400">{ad.platform || platform}</span>
                              </div>
                              <h4 className="text-sm font-bold text-white italic">"{ad.headline}"</h4>
                              <p className="text-xs text-gray-300 mt-2 whitespace-pre-wrap">{ad.body}</p>
                            </div>
                            <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[10px] text-gray-400 font-semibold">
                              <span>CTA Target:</span>
                              <span className="bg-indigo-600/20 px-2 py-0.5 rounded text-indigo-400">{ad.cta || 'Learn More'}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 5. SOCIAL MEDIA POSTS */}
                {activeTab === 'social_posts' && (
                  <div className="space-y-6">
                    <GlassCard className="border border-white/5">
                      <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4 flex-wrap gap-2">
                        <div>
                          <h3 className="text-base font-bold text-white">Generated Social Media Posts</h3>
                          <p className="text-xs text-gray-400 mt-0.5">Custom posts matching your campaign goals. Click "Publish Post" to copy to your clipboard and open the platform.</p>
                        </div>
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/10">
                          {(() => {
                            const selectedPlats = platform.split(',').map(p => p.trim().toLowerCase()).filter(Boolean);
                            return Array.isArray(result.social_media_posts)
                              ? result.social_media_posts.filter(post => {
                                  const postPlatform = (post.platform || "").toLowerCase();
                                  return selectedPlats.some(p => postPlatform.includes(p) || p.includes(postPlatform));
                                }).length
                              : 0;
                          })()} Posts Ready
                        </span>
                      </div>

                      <div className="grid grid-cols-1 gap-6">
                        {Array.isArray(result.social_media_posts) && result.social_media_posts.length > 0 ? (
                          (() => {
                            const selected = platform.split(',').map(p => p.trim().toLowerCase()).filter(Boolean);
                            const displayedPosts = result.social_media_posts.map((post, originalIdx) => {
                              const postPlatform = (post.platform || "").toLowerCase();
                              const isSelected = selected.some(p => postPlatform.includes(p) || p.includes(postPlatform));
                              if (!isSelected) return null;

                              const postStatus = postingStates[originalIdx] || 'idle';
                              const isLinkedIn = post.platform?.toLowerCase().includes('linkedin');
                              const isTwitter = post.platform?.toLowerCase().includes('twitter') || post.platform?.toLowerCase().includes('x');
                              const isFacebook = post.platform?.toLowerCase().includes('facebook');
                              const isWhatsApp = post.platform?.toLowerCase().includes('whatsapp');
                              const isGoogle = post.platform?.toLowerCase().includes('google') || post.platform?.toLowerCase().includes('search');

                              let platformBadge = "bg-white/5 text-gray-300";
                              if (isLinkedIn) platformBadge = "bg-blue-600/20 text-blue-400 border border-blue-500/20";
                              else if (isTwitter) platformBadge = "bg-slate-950/40 text-slate-200 border border-slate-700/30";
                              else if (isFacebook) platformBadge = "bg-indigo-600/20 text-indigo-400 border border-indigo-500/20";
                              else if (isWhatsApp) platformBadge = "bg-emerald-600/20 text-emerald-400 border border-emerald-500/20";
                              else if (isGoogle) platformBadge = "bg-amber-600/20 text-amber-400 border border-amber-500/20";

                              return (
                                <div key={originalIdx} className="bg-white/2 p-5 rounded-2xl border border-white/5 flex flex-col justify-between space-y-4 hover:border-white/10 transition-all">
                                  <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center space-x-2">
                                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg ${platformBadge}`}>
                                          {post.platform || 'Social Media'}
                                        </span>
                                      </div>
                                      <div className="flex items-center text-xs text-gray-400 font-semibold">
                                        <span>Generated Campaign Asset</span>
                                      </div>
                                    </div>

                                    <div className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap bg-white/2 p-4 rounded-xl border border-white/5 font-normal mb-1">
                                      {post.copy}
                                    </div>
                                    <span className="text-[10px] text-gray-500 italic block pl-1">
                                      ℹ️ Clicking Publish will copy the text to your clipboard. Paste (Ctrl+V) it to share.
                                    </span>
                                  </div>

                                  <div className="pt-4 border-t border-white/5 flex justify-end">
                                    <button
                                      onClick={() => handlePublishPost(originalIdx, post)}
                                      disabled={postStatus === 'posting'}
                                      className={`px-5 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 border shadow-lg ${
                                        postStatus === 'success'
                                          ? 'bg-emerald-600/20 text-emerald-400 border-emerald-500/20 shadow-emerald-500/5 hover:bg-emerald-600/30'
                                          : postStatus === 'posting'
                                          ? 'bg-indigo-600/20 text-indigo-400 border-indigo-500/10 shadow-indigo-500/5'
                                          : 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500/35 hover:shadow-indigo-500/10'
                                      }`}
                                    >
                                      {postStatus === 'posting' ? (
                                        <>
                                          <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin shrink-0"></div>
                                          <span>Opening...</span>
                                        </>
                                      ) : postStatus === 'success' ? (
                                        <>
                                          <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
                                          <span>Copied & Opened!</span>
                                        </>
                                      ) : (
                                        <>
                                          <Share2 className="w-3.5 h-3.5 shrink-0" />
                                          <span>Publish Post</span>
                                        </>
                                      )}
                                    </button>
                                  </div>
                                </div>
                              );
                            }).filter(Boolean);

                            if (displayedPosts.length === 0) {
                              return (
                                <div className="text-center py-8 text-xs text-gray-500">
                                  No social media posts generated for the selected platforms.
                                </div>
                              );
                            }
                            return displayedPosts;
                          })()
                        ) : (
                          <div className="text-center py-8 text-xs text-gray-500">
                            No social media posts generated for this campaign.
                          </div>
                        )}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 5. CALENDAR SCHEDULE */}
                {activeTab === 'calendar' && (
                  <GlassCard>
                    <h3 className="text-base font-bold text-white mb-4">Execution Calendar Timeline</h3>
                    <div className="space-y-4 relative border-l border-white/5 ml-4 pl-6">
                      {(result.calendar || []).map((week, idx) => (
                        <div key={idx} className="relative">
                          {/* Dot marker */}
                          <div className="absolute -left-[31px] top-1.5 w-4.5 h-4.5 rounded-full bg-indigo-600 border border-surface-900 flex items-center justify-center text-[8px] font-bold text-white">
                            {week.week}
                          </div>
                          <div>
                            <span className="text-[10px] text-indigo-400 uppercase tracking-wider font-semibold">Week {week.week}</span>
                            <h4 className="text-sm font-bold text-white mt-0.5">{week.theme}</h4>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {(week.tasks || []).map((tsk, i) => (
                                <span key={i} className="text-xs bg-white/2 px-2.5 py-1 rounded-lg border border-white/5 text-gray-300">{tsk}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <ChatAssistant domain="campaign" contextData={result} getCsrfToken={getCsrfToken} />

      {/* Toast Notification Overlay */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 animate-fade-in bg-slate-950/90 border text-white px-5 py-3.5 rounded-2xl shadow-2xl backdrop-blur-md flex items-center space-x-3.5 min-w-[320px] transition-all ${
          toast.type === 'error' ? 'border-rose-500/35 shadow-rose-500/5' : 'border-emerald-500/35 shadow-emerald-500/5'
        }`}>
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
            toast.type === 'error' ? 'bg-rose-600/20 border border-rose-500/20 text-rose-400' : 'bg-emerald-600/20 border border-emerald-500/20 text-emerald-400'
          }`}>
            {toast.type === 'error' ? <HelpCircle className="w-5 h-5 animate-pulse" /> : <CheckCircle className="w-5 h-5 animate-pulse" />}
          </div>
          <div>
            <p className={`text-[10px] font-bold uppercase tracking-widest ${
              toast.type === 'error' ? 'text-rose-400' : 'text-emerald-400'
            }`}>
              {toast.type === 'error' ? 'Notification' : 'Social Publish'}
            </p>
            <p className="text-xs font-medium text-gray-300 mt-0.5">{toast.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}
