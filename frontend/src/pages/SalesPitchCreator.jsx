import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  FileText, 
  Sparkles, 
  Download, 
  Mail, 
  HelpCircle,
  ShieldAlert,
  ClipboardList,
  MessageSquare,
  MessageCircle,
  Percent,
  CheckCircle
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';
import ChatAssistant from '../components/ChatAssistant.jsx';

export default function SalesPitchCreator({ getCsrfToken }) {
  const [product, setProduct] = useState('');
  const [customer, setCustomer] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [usp, setUsp] = useState('');
  const [painPoints, setPainPoints] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('pitch');
  const [error, setError] = useState('');
  const [suggesting, setSuggesting] = useState(false);
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
                if (r.input_dict.customer !== undefined) setCustomer(r.input_dict.customer || '');
                if (r.input_dict.target_role !== undefined) setTargetRole(r.input_dict.target_role || r.input_dict.targetRole || '');
                if (r.input_dict.usp !== undefined) setUsp(r.input_dict.usp || '');
                if (r.input_dict.pain_points !== undefined) setPainPoints(r.input_dict.pain_points || r.input_dict.painPoints || '');
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
        body: JSON.stringify({ module: 'pitch' })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.success && data.suggestions) {
          const s = data.suggestions;
          setProduct(s.product || '');
          setCustomer(s.customer || '');
          setTargetRole(s.targetRole || '');
          setUsp(s.usp || '');
          setPainPoints(s.painPoints || '');
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
    if (!product || !customer) {
      setError('Please fill in both the Product and Customer Persona fields.');
      return;
    }
    setError('');
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch('/api/v2/pitch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          product,
          customer,
          target_role: targetRole,
          usp,
          pain_points: painPoints
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setResult(data.data);
      } else {
        setError(data.error || 'Failed to generate sales pitch. Check your environment configuration.');
      }
    } catch (err) {
      console.error(err);
      setError('Network communication error. Please try again.');
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
          module: 'pitch',
          title: `Sales Pitch: ${product}`,
          data: result
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `marketmind_pitch_${product.replace(/\s+/g, '_').toLowerCase()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        alert('PDF Export failed.');
      }
    } catch (err) {
      console.error(err);
      alert('Error exporting PDF.');
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Sales Pitch Creator</h1>
        <p className="text-gray-400 mt-1">Develop personalized sales materials, elevator pitches, and objection mitigation scripts.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Config card */}
        <GlassCard className="lg:col-span-1 border border-white/5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-6">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Sales Parameters</h2>
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
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Product or Service</label>
              <input
                type="text"
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                placeholder="e.g. Enterprise Cloud Analytics"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Customer / Company Type</label>
              <input
                type="text"
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
                placeholder="e.g. Fortune 500 retail chains"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Target Buyer Title</label>
              <input
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Director of Operations"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Unique Selling Points (USPs)</label>
              <textarea
                value={usp}
                onChange={(e) => setUsp(e.target.value)}
                placeholder="e.g. 10x faster report compilation, zero coding integrations"
                rows="2"
                className="w-full glass-input"
              ></textarea>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Key Customer Pain Points</label>
              <textarea
                value={painPoints}
                onChange={(e) => setPainPoints(e.target.value)}
                placeholder="e.g. high overhead cost, delayed insights compilation"
                rows="2"
                className="w-full glass-input"
              ></textarea>
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
                  <FileText className="w-4 h-4" />
                  <span>Build Sales Pitch</span>
                </>
              )}
            </button>
          </form>
        </GlassCard>

        {/* Results view */}
        <div className="lg:col-span-2">
          {loading && (
            <GlassCard className="h-96 flex flex-col items-center justify-center space-y-4 border border-white/5 bg-surface-800/20">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white">Drafting Personalized Pitch Materials</h3>
                <p className="text-xs text-gray-500 mt-1">Calling LangGraph sales orchestrator agent nodes...</p>
              </div>
            </GlassCard>
          )}

          {!loading && !result && (
            <GlassCard className="h-96 flex flex-col items-center justify-center text-center space-y-4 border border-white/5">
              <HelpCircle className="w-12 h-12 text-gray-600" />
              <div>
                <h3 className="text-lg font-semibold text-white">No active pitch generated</h3>
                <p className="text-xs text-gray-500 mt-1">Configure parameters on the left to begin.</p>
              </div>
            </GlassCard>
          )}

          {!loading && result && (
            <div className="space-y-6">
              {/* Header card */}
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

                <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-bold">Sales assets</span>
                <h2 className="text-2xl font-display font-extrabold text-white mt-1">
                  Custom Pitch: {product}
                </h2>

                <div className="flex items-center space-x-6 mt-6 pt-6 border-t border-white/5">
                  <div className="bg-white/2 px-4 py-3 rounded-xl border border-white/5 flex items-center space-x-3">
                    <Percent className="w-5 h-5 text-indigo-400" />
                    <div>
                      <span className="text-[10px] text-gray-400 block uppercase tracking-wider">Fit Score</span>
                      <span className="text-base font-bold text-white block">{result.sales_readiness_score || 75}/100</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-400 leading-relaxed max-w-md">
                    Pitch specifically personalized for the <strong>{result.buyer_persona?.title || targetRole}</strong> role.
                  </div>
                </div>
              </GlassCard>

              {/* Tabs list */}
              <div className="flex border-b border-white/5 text-sm">
                {[
                  { id: 'pitch', label: 'Pitch & Value', icon: Sparkles },
                  { id: 'questions', label: 'Discovery Call', icon: MessageSquare },
                  { id: 'objections', label: 'Objection Handler', icon: ShieldAlert },
                  { id: 'collateral', label: 'Collateral scripts', icon: ClipboardList },
                  { id: 'outreach', label: 'Outreach templates', icon: Mail }
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

              {/* Tab views */}
              <div className="min-h-96">
                {/* 1. PITCH */}
                {activeTab === 'pitch' && (
                  <GlassCard className="space-y-6">
                    <div>
                      <h3 className="text-base font-bold text-white mb-2">30-Second Elevator Pitch</h3>
                      <p className="text-sm text-indigo-200 leading-relaxed font-medium italic">
                        "{result.elevator_pitch}"
                      </p>
                    </div>

                    <div className="pt-6 border-t border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">{result.value_proposition?.headline || 'Core Value Propositions'}</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {(Array.isArray(result.value_proposition?.benefits) ? result.value_proposition.benefits : []).map((ben, i) => (
                          <div key={i} className="bg-white/2 p-3.5 rounded-xl border border-white/5 flex items-start space-x-3">
                            <CheckCircle className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                            <span className="text-xs text-gray-300 leading-relaxed">{typeof ben === 'object' && ben !== null ? JSON.stringify(ben) : ben}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="pt-6 border-t border-white/5 bg-emerald-950/5 p-4 rounded-xl border border-emerald-500/10">
                      <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                        <span>ROI Argument & Projections</span>
                      </h3>
                      <p className="text-xs text-gray-300 mt-2 font-medium">
                        {result.roi_argument?.headline || 'Clear return on business integration:'}
                      </p>
                      <p className="text-xs text-emerald-400 font-bold mt-1">
                        Calculation: {result.roi_argument?.roi_calculation} (Timeframe: {result.roi_argument?.timeframe || '6-12 months'})
                      </p>
                    </div>
                  </GlassCard>
                )}

                {/* 2. DISCOVERY CALL */}
                {activeTab === 'questions' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Discovery Questions */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Discovery Questions</h3>
                      <div className="space-y-2">
                        {(Array.isArray(result.discovery_questions) ? result.discovery_questions : []).map((q, i) => (
                          <div key={i} className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs text-gray-300 flex items-start space-x-2">
                            <span className="text-indigo-400 font-bold">{i+1}.</span>
                            <span>{typeof q === 'object' && q !== null ? JSON.stringify(q) : q}</span>
                          </div>
                        ))}
                      </div>
                    </GlassCard>

                    {/* Meeting Agenda */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Discovery Meeting Agenda</h3>
                      <div className="space-y-3 pl-4 border-l border-white/5">
                        {(Array.isArray(result.meeting_agenda) ? result.meeting_agenda : []).map((ag, i) => (
                          <div key={i} className="relative text-xs text-gray-300">
                            <div className="absolute -left-[23px] top-1 w-2.5 h-2.5 rounded-full bg-indigo-500"></div>
                            <span className="font-semibold text-white block">Step {i+1}</span>
                            <span className="text-gray-400">
                              {typeof ag === 'object' && ag !== null 
                                ? `${ag.time ? `[${ag.time}] ` : ''}${ag.topic || ''}${ag.goal ? ` - Goal: ${ag.goal}` : ''}`
                                : ag}
                            </span>
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 3. OBJECTIONS */}
                {activeTab === 'objections' && (
                  <div className="space-y-4">
                    {(Array.isArray(result.objection_handling) ? result.objection_handling : []).map((item, idx) => (
                      <GlassCard key={idx} className="border border-white/5">
                        <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs uppercase tracking-wider mb-2">
                          <ShieldAlert className="w-4 h-4" />
                          <span>Objection: {item.objection}</span>
                        </div>
                        <div className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs text-gray-300 leading-relaxed">
                          <strong>Strategic Response:</strong> {item.response}
                        </div>
                      </GlassCard>
                    ))}
                  </div>
                )}

                {/* 4. COLLATERAL */}
                {activeTab === 'collateral' && (
                  <div className="space-y-6">
                    {/* Closing Script */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-2">Interactive Closing Script</h3>
                      <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap italic">
                        {result.closing_script}
                      </p>
                    </GlassCard>

                    {/* Proposal Outline */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Proposal Section Outline</h3>
                      <div className="grid grid-cols-2 gap-3 text-xs text-gray-300">
                        {(Array.isArray(result.proposal_outline) ? result.proposal_outline : []).map((sec, i) => (
                          <div key={i} className="bg-white/2 p-2.5 rounded-lg border border-white/5 flex items-center space-x-2">
                            <span className="w-5 h-5 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-bold text-[10px]">{i+1}</span>
                            <span>{typeof sec === 'object' && sec !== null ? JSON.stringify(sec) : sec}</span>
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 5. EMAIL OUTREACH */}
                {activeTab === 'outreach' && (
                  <div className="space-y-6">
                    {/* Cold Email */}
                    <GlassCard className="border border-white/5">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-base font-bold text-white flex items-center space-x-2">
                          <Mail className="w-5 h-5 text-indigo-400" />
                          <span>Cold Email Cadence Template</span>
                        </h3>
                      </div>
                      <div className="bg-surface-900/60 p-4 rounded-xl border border-white/5 text-xs font-mono space-y-3 text-gray-300">
                        <div>
                          <strong>Subject:</strong> {result.email_template?.subject || 'Product integration opportunities'}
                        </div>
                        <div className="border-t border-white/5 pt-3 whitespace-pre-wrap">
                          {result.email_template?.body}
                        </div>
                      </div>
                    </GlassCard>

                    {/* LinkedIn outreach */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white flex items-center space-x-2 mb-4">
                        <MessageCircle className="w-5 h-5 text-cyan-400" />
                        <span>LinkedIn Connection Message</span>
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="bg-surface-900/60 p-4 rounded-xl border border-white/5">
                          <span className="text-[10px] text-gray-500 font-bold block uppercase mb-1">Connection Invitation (≤300 Chars)</span>
                          <p className="text-gray-300 italic">"{result.linkedin_template?.connection_note}"</p>
                        </div>
                        <div className="bg-surface-900/60 p-4 rounded-xl border border-white/5">
                          <span className="text-[10px] text-gray-500 font-bold block uppercase mb-1">Follow-up Message (≤500 Chars)</span>
                          <p className="text-gray-300 italic">"{result.linkedin_template?.follow_up}"</p>
                        </div>
                      </div>
                    </GlassCard>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <ChatAssistant domain="pitch" contextData={result} getCsrfToken={getCsrfToken} />
    </div>
  );
}
