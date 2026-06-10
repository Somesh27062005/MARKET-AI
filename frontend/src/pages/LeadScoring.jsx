import React, { useState } from 'react';
import { 
  UserCheck, 
  Sparkles, 
  Download, 
  TrendingUp, 
  AlertTriangle,
  UserCheck2,
  Bookmark,
  CheckCircle,
  HelpCircle,
  FolderPlus,
  Coins,
  ShieldCheck,
  Calendar,
  Activity,
  MessageSquare
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';
import ChatAssistant from '../components/ChatAssistant.jsx';

export default function LeadScoring({ getCsrfToken }) {
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [industry, setIndustry] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [decisionRole, setDecisionRole] = useState('');
  const [budget, setBudget] = useState('');
  const [need, setNeed] = useState('');
  const [urgency, setUrgency] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('bant');
  const [error, setError] = useState('');
  const [crmStatus, setCrmStatus] = useState('');
  const [suggesting, setSuggesting] = useState(false);

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
        body: JSON.stringify({ module: 'lead' })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.success && data.suggestions) {
          const s = data.suggestions;
          setName(s.name || '');
          setCompany(s.company || '');
          setIndustry(s.industry || '');
          setCompanySize(s.companySize || '');
          setDecisionRole(s.decisionRole || '');
          setBudget(s.budget || '');
          setNeed(s.need || '');
          setUrgency(s.urgency || '');
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
    if (!name || !budget || !need) {
      setError('Name, Budget, and Need fields are required for analysis.');
      return;
    }
    setError('');
    setCrmStatus('');
    setResult(null);
    setLoading(true);

    try {
      const res = await fetch('/api/v2/lead_score', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          name,
          company,
          industry,
          company_size: companySize,
          decision_role: decisionRole,
          budget,
          need,
          urgency
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setResult(data.data);
      } else {
        setError(data.error || 'Failed to qualify lead. Check Groq API configuration.');
      }
    } catch (err) {
      console.error(err);
      setError('Communication error. Verify backend status.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCRM = async () => {
    if (!result) return;
    setCrmStatus('exporting');
    
    // Map numerical score to standard A/B/C/D grade
    let grade = 'C';
    const score = result.lead_score || 50;
    if (score >= 90) grade = 'A+';
    else if (score >= 80) grade = 'A';
    else if (score >= 70) grade = 'B';
    else if (score >= 60) grade = 'C';
    else grade = 'D';

    try {
      const res = await fetch('/api/crm/leads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          name,
          company: company || 'Self/Individual',
          score: score,
          grade: grade,
          details: result.qualification_summary || 'AI qualified lead'
        })
      });

      if (res.ok) {
        setCrmStatus('success');
      } else {
        setCrmStatus('failed');
      }
    } catch (err) {
      console.error(err);
      setCrmStatus('failed');
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
          module: 'lead',
          title: `Lead Qualification: ${name}`,
          data: result
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `marketmind_lead_${name.replace(/\s+/g, '_').toLowerCase()}.pdf`;
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
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Lead Scoring & Qualification</h1>
        <p className="text-gray-400 mt-1">Score incoming prospect profiles based on BANT metrics and buying intent.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Input panel */}
        <GlassCard className="lg:col-span-1 border border-white/5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-6">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Lead Details</h2>
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
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Lead Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Johnathan Vance"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Company Name</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Acme Corp"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Industry Sector</label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Logistics & Supply Chain"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Company Size</label>
              <input
                type="text"
                value={companySize}
                onChange={(e) => setCompanySize(e.target.value)}
                placeholder="e.g. 100-500 employees"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Decision-Maker Role</label>
              <input
                type="text"
                value={decisionRole}
                onChange={(e) => setDecisionRole(e.target.value)}
                placeholder="e.g. VP Operations"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Stated Budget / Range</label>
              <input
                type="text"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="e.g. $80,000 annually"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Core Need / Solution Requirement</label>
              <textarea
                value={need}
                onChange={(e) => setNeed(e.target.value)}
                placeholder="e.g. needs automated inventory tracking, low-code integration"
                rows="3"
                className="w-full glass-input"
              ></textarea>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Timeline / Urgency</label>
              <input
                type="text"
                value={urgency}
                onChange={(e) => setUrgency(e.target.value)}
                placeholder="e.g. Q4 implementation, budget signed"
                className="w-full glass-input"
              />
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
                  <UserCheck className="w-4 h-4" />
                  <span>Analyze Lead Fit</span>
                </>
              )}
            </button>
          </form>
        </GlassCard>

        {/* Qualification screen */}
        <div className="lg:col-span-2">
          {loading && (
            <GlassCard className="h-96 flex flex-col items-center justify-center space-y-4 border border-white/5 bg-surface-800/20">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white">Running Predictive Scoring Algorithm</h3>
                <p className="text-xs text-gray-500 mt-1">Evaluating budget qualification and purchasing authority...</p>
              </div>
            </GlassCard>
          )}

          {!loading && !result && (
            <GlassCard className="h-96 flex flex-col items-center justify-center text-center space-y-4 border border-white/5">
              <HelpCircle className="w-12 h-12 text-gray-600" />
              <div>
                <h3 className="text-lg font-semibold text-white">No lead scored yet</h3>
                <p className="text-xs text-gray-500 mt-1">Configure prospect variables on the left to start qualification.</p>
              </div>
            </GlassCard>
          )}

          {!loading && result && (
            <div className="space-y-6">
              {/* Scorecard card */}
              <GlassCard className="border border-indigo-500/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 flex items-center space-x-2">
                  <button 
                    onClick={handleExportCRM}
                    disabled={crmStatus === 'exporting' || crmStatus === 'success'}
                    className="p-2 text-indigo-400 hover:text-white hover:bg-indigo-600/10 rounded-xl border border-indigo-500/10 transition-all flex items-center space-x-1.5 text-xs font-semibold"
                  >
                    <FolderPlus className="w-4 h-4" />
                    <span>
                      {crmStatus === 'exporting' && 'Exporting...'}
                      {crmStatus === 'success' && 'Exported to CRM'}
                      {crmStatus === 'failed' && 'Retry Export'}
                      {!crmStatus && 'Add to CRM Pipeline'}
                    </span>
                  </button>
                  <button 
                    onClick={handleExportPDF}
                    className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl border border-white/5 transition-all flex items-center space-x-1.5 text-xs font-semibold"
                  >
                    <Download className="w-4 h-4" />
                    <span>PDF</span>
                  </button>
                </div>

                <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-bold">Qualification report</span>
                <h2 className="text-2xl font-display font-extrabold text-white mt-1">
                  Lead: {name} {company && `(${company})`}
                </h2>

                <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-white/5">
                  <div className="text-center bg-white/2 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Lead Score</span>
                    <span className="text-xl font-bold text-indigo-400 mt-1 block">{result.lead_score || 50}/100</span>
                  </div>
                  <div className="text-center bg-white/2 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Intent Level</span>
                    <span className={`text-xl font-bold mt-1 block ${result.temperature === 'Hot' ? 'text-rose-400' : result.temperature === 'Warm' ? 'text-amber-400' : 'text-cyan-400'}`}>
                      {result.temperature || 'Warm'}
                    </span>
                  </div>
                  <div className="text-center bg-white/2 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Conversion Chance</span>
                    <span className="text-xl font-bold text-emerald-400 mt-1 block">{result.conversion_probability || 35}%</span>
                  </div>
                </div>
              </GlassCard>

              {/* Tabs selector */}
              <div className="flex border-b border-white/5 text-sm">
                {[
                  { id: 'bant', label: 'BANT Scorecard', icon: Bookmark },
                  { id: 'intent', label: 'Intent & Risks', icon: Activity },
                  { id: 'actions', label: 'Sales Playbook', icon: UserCheck2 }
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

              {/* Tab Panels */}
              <div className="min-h-96">
                {/* 1. BANT */}
                {activeTab === 'bant' && (
                  <div className="space-y-4">
                    {/* Qualification Summary */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-sm font-bold text-white mb-2">Qualification Executive Summary</h3>
                      <p className="text-xs text-gray-300 leading-relaxed">
                        {result.qualification_summary}
                      </p>
                    </GlassCard>

                    {/* BANT Breakdown */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        { label: 'Budget', icon: Coins, data: result.bant?.budget },
                        { label: 'Authority', icon: ShieldCheck, data: result.bant?.authority },
                        { label: 'Need', icon: Sparkles, data: result.bant?.need },
                        { label: 'Timeline', icon: Calendar, data: result.bant?.timeline }
                      ].map((card, i) => {
                        const Icon = card.icon;
                        const score = card.data?.score || 0;
                        return (
                          <GlassCard key={i} className="border border-white/5 flex flex-col justify-between">
                            <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                              <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                                <Icon className="w-4 h-4 text-indigo-400" />
                                <span>{card.label} Fit</span>
                              </h4>
                              <span className="text-xs font-bold text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded">
                                Score: {score}/100
                              </span>
                            </div>
                            <div className="text-xs text-gray-300 space-y-2">
                              <p><strong>Assessment:</strong> {card.data?.assessment || 'Evaluating lead data fit...'}</p>
                              {card.data?.evidence && <p className="text-gray-400 italic">"Evidence: {card.data.evidence}"</p>}
                            </div>
                          </GlassCard>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 2. INTENT & RISKS */}
                {activeTab === 'intent' && (
                  <div className="space-y-6">
                    {/* Intent Signals */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Buying Intent Signals</h3>
                      <div className="space-y-3">
                        {(Array.isArray(result.buying_intent?.signals) ? result.buying_intent.signals : []).map((sig, idx) => (
                          <div key={idx} className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs flex justify-between items-start">
                            <div className="space-y-1">
                              <h4 className="font-bold text-white">{sig.signal}</h4>
                              <p className="text-gray-400">{sig.evidence}</p>
                            </div>
                            <span className="text-[10px] font-bold bg-indigo-500/10 text-indigo-400 px-2 py-1 rounded">
                              Strength: {sig.strength || 'Medium'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </GlassCard>

                    {/* Risk Factors */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Identified Risk Factors</h3>
                      <div className="space-y-3">
                        {(Array.isArray(result.risk_factors) ? result.risk_factors : []).map((risk, idx) => (
                          <div key={idx} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs">
                            <div className="flex items-center justify-between font-bold text-white mb-2">
                              <h4 className="flex items-center space-x-2">
                                <AlertTriangle className="w-4 h-4 text-rose-400" />
                                <span>{risk.risk}</span>
                              </h4>
                              <span className="text-[10px] uppercase font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded">
                                Impact: {risk.impact || 'Medium'}
                              </span>
                            </div>
                            <p className="text-gray-400"><strong>Mitigation:</strong> {risk.mitigation}</p>
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 3. SALES PLAYBOOK */}
                {activeTab === 'actions' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Recommended Actions */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Recommended Actions</h3>
                      <div className="space-y-2">
                        {(Array.isArray(result.recommended_actions) ? result.recommended_actions : []).map((act, i) => (
                          <div key={i} className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs text-gray-300 flex items-start space-x-2">
                            <CheckCircle className="w-4.5 h-4.5 text-indigo-400 shrink-0 mt-0.5" />
                            <span>
                              {typeof act === 'object' && act !== null 
                                ? `${act.action || ''}${act.timeline ? ` (Timeline: ${act.timeline})` : ''}`
                                : act}
                            </span>
                          </div>
                        ))}
                      </div>
                    </GlassCard>

                    {/* Next Best Action */}
                    <GlassCard className="border border-indigo-500/10 bg-indigo-950/10">
                      <h3 className="text-base font-bold text-white mb-2">Next Best Action</h3>
                      <p className="text-xs text-gray-300 leading-relaxed mb-4">
                        We recommend prioritizing the following step to maximize closing probability:
                      </p>
                      <div className="bg-surface-900/60 p-4 rounded-xl border border-indigo-500/20 text-xs text-indigo-200 font-semibold italic">
                        "{result.next_best_action}"
                      </div>
                    </GlassCard>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <ChatAssistant domain="lead" contextData={result} getCsrfToken={getCsrfToken} />
    </div>
  );
}
