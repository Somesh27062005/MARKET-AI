import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  Lightbulb, 
  Sparkles, 
  Download, 
  HelpCircle,
  AlertTriangle,
  ClipboardList,
  CheckCircle,
  Map,
  Compass,
  ArrowUpRight,
  ShieldAlert,
  MessageSquare
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';
import ChatAssistant from '../components/ChatAssistant.jsx';

export default function BusinessInsights({ getCsrfToken }) {
  const [businessType, setBusinessType] = useState('');
  const [challenges, setChallenges] = useState('');
  const [goals, setGoals] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [industryContext, setIndustryContext] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('diagnostic');
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
                if (r.input_dict.business_type !== undefined) setBusinessType(r.input_dict.business_type || r.input_dict.businessType || '');
                if (r.input_dict.challenges !== undefined) setChallenges(r.input_dict.challenges || '');
                if (r.input_dict.goals !== undefined) setGoals(r.input_dict.goals || '');
                if (r.input_dict.target_audience !== undefined) setTargetAudience(r.input_dict.target_audience || r.input_dict.targetAudience || '');
                if (r.input_dict.industry_context !== undefined) setIndustryContext(r.input_dict.industry_context || r.input_dict.industryContext || '');
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
        body: JSON.stringify({ module: 'insights' })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.success && data.suggestions) {
          const s = data.suggestions;
          setBusinessType(s.businessType || '');
          setChallenges(s.challenges || '');
          setGoals(s.goals || '');
          setTargetAudience(s.targetAudience || '');
          setIndustryContext(s.industryContext || '');
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
    if (!businessType || !challenges) {
      setError('Business Type and Current Challenges are required.');
      return;
    }
    setError('');
    setResult(null);
    setLoading(true);

    try {
      const res = await fetch('/api/v2/business_insights', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          business_type: businessType,
          challenges,
          goals,
          target_audience: targetAudience,
          industry_context: industryContext
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setResult(data.data);
      } else {
        setError(data.error || 'Failed to generate business insights.');
      }
    } catch (err) {
      console.error(err);
      setError('Communication error. Verify server.');
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
          module: 'insights',
          title: `Strategic Insights: ${businessType}`,
          data: result
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `marketmind_insights_${businessType.replace(/\s+/g, '_').toLowerCase()}.pdf`;
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
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Business Insights & Diagnostics</h1>
        <p className="text-gray-400 mt-1">Audit company operations, execute root-cause diagnostics, and unlock 30/60/90 action roadmaps.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Config card */}
        <GlassCard className="lg:col-span-1 border border-white/5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-6">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Advisory inputs</h2>
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
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Business model / Type</label>
              <input
                type="text"
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value)}
                placeholder="e.g. B2B SaaS Enterprise"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Key Operational Challenges</label>
              <textarea
                value={challenges}
                onChange={(e) => setChallenges(e.target.value)}
                placeholder="e.g. high customer acquisition cost, churn rate is 15%, low sales win rate"
                rows="3"
                className="w-full glass-input"
              ></textarea>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Strategic Goals</label>
              <textarea
                value={goals}
                onChange={(e) => setGoals(e.target.value)}
                placeholder="e.g. double ARR in 12 months, expand to European markets"
                rows="2"
                className="w-full glass-input"
              ></textarea>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Target Audience Context</label>
              <input
                type="text"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="e.g. Mid-market IT managers"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Industry Landscape</label>
              <input
                type="text"
                value={industryContext}
                onChange={(e) => setIndustryContext(e.target.value)}
                placeholder="e.g. highly competitive SaaS marketplace"
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
                  <Lightbulb className="w-4 h-4" />
                  <span>Diagnose Business</span>
                </>
              )}
            </button>
          </form>
        </GlassCard>

        {/* Results area */}
        <div className="lg:col-span-2">
          {loading && (
            <GlassCard className="h-96 flex flex-col items-center justify-center space-y-4 border border-white/5 bg-surface-800/20">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white">Performing Full Business Diagnostics</h3>
                <p className="text-xs text-gray-500 mt-1">LLM advisory agent is analyzing root causes and roadmap timelines...</p>
              </div>
            </GlassCard>
          )}

          {!loading && !result && (
            <GlassCard className="h-96 flex flex-col items-center justify-center text-center space-y-4 border border-white/5">
              <HelpCircle className="w-12 h-12 text-gray-600" />
              <div>
                <h3 className="text-lg font-semibold text-white">No active diagnostics run</h3>
                <p className="text-xs text-gray-500 mt-1">Complete advisory details on the left to trigger strategy mapping.</p>
              </div>
            </GlassCard>
          )}

          {!loading && result && (
            <div className="space-y-6">
              {/* Header scorecard */}
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

                <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-bold">Diagnostics summary</span>
                <h2 className="text-2xl font-display font-extrabold text-white mt-1">
                  Strategic Advisor Report
                </h2>

                <div className="flex items-center space-x-6 mt-6 pt-6 border-t border-white/5">
                  <div className="bg-white/2 px-4 py-3 rounded-xl border border-white/5 flex items-center space-x-3">
                    <Compass className="w-5 h-5 text-indigo-400 animate-spin-slow" />
                    <div>
                      <span className="text-[10px] text-gray-400 block uppercase tracking-wider">Business Health</span>
                      <span className="text-base font-bold text-white block">{result.opportunity_score || 65}/100</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-400 leading-relaxed max-w-md">
                    Opportunity Score reflects competitive posture, operational risks, and current revenue efficiency.
                  </div>
                </div>
              </GlassCard>

              {/* Navigation tabs */}
              <div className="flex border-b border-white/5 text-sm">
                {[
                  { id: 'diagnostic', label: 'Root Cause audit', icon: ClipboardList },
                  { id: 'opportunities', label: 'Growth areas', icon: Sparkles },
                  { id: 'recommendations', label: 'Strategy Recs', icon: Lightbulb },
                  { id: 'roadmap', label: '30/60/90 Plan', icon: Map }
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
                {/* 1. DIAGNOSTICS */}
                {activeTab === 'diagnostic' && (
                  <div className="space-y-4">
                    {/* Executive Summary */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-sm font-bold text-white mb-2">Executive Advisory Narrative</h3>
                      <p className="text-xs text-gray-300 leading-relaxed">
                        {result.executive_summary}
                      </p>
                    </GlassCard>

                    {/* Challenges Severity */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-sm font-bold text-white mb-3">Operational Challenges</h3>
                      <div className="space-y-3">
                        {(Array.isArray(result.current_challenges) ? result.current_challenges : []).map((ch, idx) => (
                          <div key={idx} className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs flex justify-between items-center">
                            <div>
                              <h4 className="font-bold text-white">{ch.challenge || ch}</h4>
                              {ch.impact && <p className="text-gray-400 mt-1">{ch.impact}</p>}
                            </div>
                            {ch.severity && (
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${ch.severity === 'High' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'}`}>
                                {ch.severity}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </GlassCard>

                    {/* Root Cause Analysis */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-sm font-bold text-white mb-3">Root Cause Diagnosis</h3>
                      <div className="space-y-3">
                        {(Array.isArray(result.root_cause_analysis) ? result.root_cause_analysis : []).map((rc, idx) => (
                          <div key={idx} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs">
                            <h4 className="font-bold text-white flex items-center space-x-2">
                              <AlertTriangle className="w-4 h-4 text-rose-400" />
                              <span>{rc.problem}</span>
                            </h4>
                            <p className="text-gray-400 mt-2"><strong>Root Cause:</strong> {rc.root_cause}</p>
                            {rc.evidence && <p className="text-[10px] text-gray-500 mt-1 italic">Evidence: {rc.evidence}</p>}
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 2. OPPORTUNITIES */}
                {activeTab === 'opportunities' && (
                  <div className="space-y-6">
                    {/* Revenue & Growth */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <GlassCard className="border border-white/5">
                        <h3 className="text-sm font-bold text-white mb-3">New Revenue Channels</h3>
                        <div className="space-y-2">
                          {(Array.isArray(result.revenue_opportunities) ? result.revenue_opportunities : []).map((opp, idx) => (
                            <div key={idx} className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs space-y-1.5">
                              <div className="flex justify-between font-bold text-white">
                                <span>{opp.source}</span>
                                <span className="text-indigo-400 whitespace-nowrap ml-2">{opp.potential}</span>
                              </div>
                              {opp.description && (
                                <p className="text-gray-400 text-[11px] leading-normal">{opp.description}</p>
                              )}
                              <span className="text-[10px] text-gray-500 block mt-1">Timeline: {opp.timeline || 'Q3'}</span>
                            </div>
                          ))}
                        </div>
                      </GlassCard>

                      <GlassCard className="border border-white/5">
                        <h3 className="text-sm font-bold text-white mb-3">Cost Optimization Areas</h3>
                        <div className="space-y-2">
                          {(Array.isArray(result.cost_optimization) ? result.cost_optimization : []).map((cost, idx) => (
                            <div key={idx} className="bg-white/2 p-3 rounded-xl border border-white/5 text-xs">
                              <div className="flex justify-between font-bold text-white">
                                <span>{cost.area}</span>
                                <span className="text-rose-400">-{cost.potential_savings}</span>
                              </div>
                              <p className="text-gray-400 mt-1">{cost.action}</p>
                            </div>
                          ))}
                        </div>
                      </GlassCard>
                    </div>

                    {/* Growth Opportunities Scored */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-base font-bold text-white mb-3">Strategic Growth Opportunities</h3>
                      <div className="space-y-3">
                        {(Array.isArray(result.growth_opportunities) ? result.growth_opportunities : []).map((opp, idx) => (
                          <div key={idx} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="space-y-1">
                              <h4 className="font-bold text-white">
                                {typeof opp === 'object' && opp !== null ? (opp.title || opp.opportunity || '') : opp}
                              </h4>
                              {opp.description && (
                                <p className="text-gray-400 text-[11px] leading-normal">{opp.description}</p>
                              )}
                              <div className="flex flex-wrap gap-2 mt-1">
                                {opp.revenue_impact && (
                                  <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-medium">
                                    Impact: {opp.revenue_impact}
                                  </span>
                                )}
                                {opp.effort && (
                                  <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded font-medium">
                                    Effort: {opp.effort}
                                  </span>
                                )}
                              </div>
                            </div>
                            {opp.score && (
                              <span className="text-[10px] font-bold bg-indigo-500/10 text-indigo-400 px-2.5 py-1 rounded-lg whitespace-nowrap self-start md:self-center">
                                Score: {opp.score}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  </div>
                )}

                {/* 3. RECOMMENDATIONS */}
                {activeTab === 'recommendations' && (
                  <div className="space-y-4">
                    {(Array.isArray(result.strategic_recommendations) ? result.strategic_recommendations : []).map((rec, idx) => (
                      <GlassCard key={idx} className="border border-white/5 flex flex-col md:flex-row justify-between gap-4">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-white">{rec.recommendation}</h4>
                          <p className="text-xs text-gray-400">Impact: {rec.impact || 'High'}</p>
                        </div>
                        <div className="flex items-center space-x-2 text-xs">
                          <span className={`px-2 py-0.5 rounded font-bold ${rec.priority === 'High' ? 'bg-indigo-600/20 text-indigo-400' : 'bg-white/5 text-gray-400'}`}>
                            Priority: {rec.priority}
                          </span>
                        </div>
                      </GlassCard>
                    ))}
                  </div>
                )}

                {/* 4. ROADMAP */}
                {activeTab === 'roadmap' && (
                  <div className="space-y-6">
                    {[
                      { title: 'Days 1-30: Foundation Phase', data: result.plan_30_day },
                      { title: 'Days 31-60: Implementation Phase', data: result.plan_60_day },
                      { title: 'Days 61-90: Scaling Phase', data: result.plan_90_day }
                    ].map((phase, pIdx) => (
                      <GlassCard key={pIdx} className="border border-white/5">
                        <h3 className="text-sm font-bold text-indigo-400 border-b border-white/5 pb-2 mb-3">
                          {phase.title}
                        </h3>
                        <div className="space-y-3">
                          {(Array.isArray(phase.data) ? phase.data : []).map((item, idx) => (
                            <div key={idx} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs space-y-2">
                              <div className="flex justify-between items-start font-bold text-white">
                                <span>{item.action}</span>
                                {item.owner && <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Owner: {item.owner}</span>}
                              </div>
                              <p className="text-gray-400">{item.description}</p>
                              {Array.isArray(item.tools) && item.tools.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 pt-1">
                                  {item.tools.map((t, ti) => (
                                    <span key={ti} className="text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded">{t}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </GlassCard>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <ChatAssistant domain="insights" contextData={result} getCsrfToken={getCsrfToken} />
    </div>
  );
}
