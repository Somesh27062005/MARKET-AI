import React, { useState } from 'react';
import { 
  TrendingUp, 
  Sparkles, 
  Download, 
  HelpCircle,
  ShieldAlert,
  ListFilter,
  BarChart2,
  Share2,
  CheckCircle,
  AlertTriangle,
  Award,
  BookOpen,
  MessageSquare
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import GlassCard from '../components/GlassCard.jsx';
import ChatAssistant from '../components/ChatAssistant.jsx';

export default function MarketAnalysis({ getCsrfToken }) {
  const [industry, setIndustry] = useState('');
  const [productCategory, setProductCategory] = useState('');
  const [targetMarket, setTargetMarket] = useState('');
  const [competitorsRaw, setCompetitorsRaw] = useState('');
  const [timeHorizon, setTimeHorizon] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('swot');
  const [error, setError] = useState('');
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
        body: JSON.stringify({ module: 'market' })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.success && data.suggestions) {
          const s = data.suggestions;
          setIndustry(s.industry || '');
          setProductCategory(s.productCategory || '');
          setTargetMarket(s.targetMarket || '');
          setCompetitorsRaw(s.competitors || '');
          setTimeHorizon(s.timeHorizon || '');
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

  const renderBulletList = (val) => {
    if (!val) return null;
    if (Array.isArray(val)) {
      return val.map((item, i) => <li key={i} className="list-disc list-inside">{item}</li>);
    }
    if (typeof val === 'string') {
      return val.split(',').map(item => item.trim()).filter(Boolean).map((item, i) => (
        <li key={i} className="list-disc list-inside">{item}</li>
      ));
    }
    return null;
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!industry) {
      setError('Please fill in the Industry field.');
      return;
    }
    setError('');
    setResult(null);
    setLoading(true);

    try {
      const res = await fetch('/api/v2/market_analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          industry,
          product_category: productCategory,
          target_market: targetMarket,
          competitors_raw: competitorsRaw,
          time_horizon: timeHorizon
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setResult(data.data);
      } else {
        setError(data.error || 'Failed to conduct market analysis. Check Groq configurations.');
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
          module: 'market',
          title: `Market Analysis: ${industry}`,
          data: result
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `marketmind_market_${industry.replace(/\s+/g, '_').toLowerCase()}.pdf`;
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

  // Recharts preparation
  const chartData = (Array.isArray(result?.growth_chart_data) ? result.growth_chart_data : []).map(d => ({
    name: d.period,
    Size: d.value
  }));

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Market Intelligence & SWOT</h1>
        <p className="text-gray-400 mt-1">Conduct deep industry research, PESTEL macro scoping, and competitor profiling.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Config card */}
        <GlassCard className="lg:col-span-1 border border-white/5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-6">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Market Parameters</h2>
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
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Industry Sector</label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Artificial Intelligence, SaaS"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Product Category</label>
              <input
                type="text"
                value={productCategory}
                onChange={(e) => setProductCategory(e.target.value)}
                placeholder="e.g. Sales Intelligence platform"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Target Market / Region</label>
              <input
                type="text"
                value={targetMarket}
                onChange={(e) => setTargetMarket(e.target.value)}
                placeholder="e.g. North America, Global"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Known Competitors (Optional)</label>
              <textarea
                value={competitorsRaw}
                onChange={(e) => setCompetitorsRaw(e.target.value)}
                placeholder="e.g. Apollo.io, ZoomInfo, Cognism"
                rows="2"
                className="w-full glass-input"
              ></textarea>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Time Horizon</label>
              <select
                value={timeHorizon}
                onChange={(e) => setTimeHorizon(e.target.value)}
                className="w-full glass-input"
              >
                <option value="12 months">12 Months</option>
                <option value="3 years">3 Years</option>
                <option value="5 years">5 Years</option>
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
                  <TrendingUp className="w-4 h-4" />
                  <span>Analyze Market</span>
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
                <h3 className="text-lg font-semibold text-white">Analyzing Industry Landscape</h3>
                <p className="text-xs text-gray-500 mt-1">AI market researcher is assessing TAM sizing, SWOT, and competitor metrics...</p>
              </div>
            </GlassCard>
          )}

          {!loading && !result && (
            <GlassCard className="h-96 flex flex-col items-center justify-center text-center space-y-4 border border-white/5">
              <HelpCircle className="w-12 h-12 text-gray-600" />
              <div>
                <h3 className="text-lg font-semibold text-white">No market analysis generated</h3>
                <p className="text-xs text-gray-500 mt-1">Configure variables on the left to pull real-time AI market scoping.</p>
              </div>
            </GlassCard>
          )}

          {!loading && result && (
            <div className="space-y-6">
              {/* Header block */}
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

                <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-bold">Market intelligence</span>
                <h2 className="text-2xl font-display font-extrabold text-white mt-1">
                  Industry: {industry}
                </h2>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-6 pt-6 border-t border-white/5 text-xs text-gray-300">
                  <div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">TAM Market Sizing</span>
                    <span className="text-sm font-bold text-white mt-1 block">
                      {result.market_size?.current || 'USD ' + (result.growth_chart_data?.[result.growth_chart_data.length - 1]?.value || '10B')}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">CAGR growth rate</span>
                    <span className="text-sm font-bold text-cyan-400 mt-1 block">{result.market_size?.cagr || '8.5%'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Time Horizon</span>
                    <span className="text-sm font-bold text-emerald-400 mt-1 block">{timeHorizon}</span>
                  </div>
                </div>
              </GlassCard>

              {/* Navigation tabs */}
              <div className="flex border-b border-white/5 text-sm">
                {[
                  { id: 'swot', label: 'SWOT Grid', icon: ShieldAlert },
                  { id: 'pestel', label: 'PESTEL Analysis', icon: BookOpen },
                  { id: 'competitors', label: 'Competitor Profiling', icon: Award },
                  { id: 'charts', label: 'Growth charts', icon: BarChart2 }
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

              {/* View body */}
              <div className="min-h-96">
                {/* 1. SWOT */}
                {activeTab === 'swot' && (
                  <div className="space-y-4">
                    {/* Executive Summary */}
                    <GlassCard className="border border-white/5">
                      <h3 className="text-sm font-bold text-white mb-2">Executive Market Summary</h3>
                      <p className="text-xs text-gray-300 leading-relaxed">
                        {result.executive_summary}
                      </p>
                    </GlassCard>

                    {/* SWOT Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Strengths */}
                      <GlassCard className="border border-emerald-500/10 bg-emerald-950/5 p-4 rounded-xl">
                        <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                          <CheckCircle className="w-4 h-4" />
                          <span>Strengths</span>
                        </h4>
                        <ul className="space-y-1.5 text-xs text-gray-300">
                          {(Array.isArray(result.swot?.strengths) ? result.swot.strengths : []).map((s, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="w-1 h-1 rounded-full bg-emerald-400 mt-1.5"></span>
                              <span>{s}</span>
                            </li>
                          ))}
                        </ul>
                      </GlassCard>

                      {/* Weaknesses */}
                      <GlassCard className="border border-rose-500/10 bg-rose-950/5 p-4 rounded-xl">
                        <h4 className="text-xs font-bold text-rose-400 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                          <AlertTriangle className="w-4 h-4" />
                          <span>Weaknesses</span>
                        </h4>
                        <ul className="space-y-1.5 text-xs text-gray-300">
                          {(Array.isArray(result.swot?.weaknesses) ? result.swot.weaknesses : []).map((w, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="w-1 h-1 rounded-full bg-rose-400 mt-1.5"></span>
                              <span>{w}</span>
                            </li>
                          ))}
                        </ul>
                      </GlassCard>

                      {/* Opportunities */}
                      <GlassCard className="border border-indigo-500/10 bg-indigo-950/5 p-4 rounded-xl">
                        <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                          <Sparkles className="w-4 h-4" />
                          <span>Opportunities</span>
                        </h4>
                        <ul className="space-y-1.5 text-xs text-gray-300">
                          {(Array.isArray(result.swot?.opportunities) ? result.swot.opportunities : []).map((o, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="w-1 h-1 rounded-full bg-indigo-400 mt-1.5"></span>
                              <span>{o}</span>
                            </li>
                          ))}
                        </ul>
                      </GlassCard>

                      {/* Threats */}
                      <GlassCard className="border border-yellow-500/10 bg-yellow-950/5 p-4 rounded-xl">
                        <h4 className="text-xs font-bold text-yellow-400 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                          <ShieldAlert className="w-4 h-4" />
                          <span>Threats</span>
                        </h4>
                        <ul className="space-y-1.5 text-xs text-gray-300">
                          {(Array.isArray(result.swot?.threats) ? result.swot.threats : []).map((t, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="w-1 h-1 rounded-full bg-yellow-400 mt-1.5"></span>
                              <span>{t}</span>
                            </li>
                          ))}
                        </ul>
                      </GlassCard>
                    </div>
                  </div>
                )}

                {/* 2. PESTEL */}
                {activeTab === 'pestel' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { key: 'political', title: 'Political Factors' },
                      { key: 'economic', title: 'Economic Factors' },
                      { key: 'social', title: 'Social Factors' },
                      { key: 'technological', title: 'Technological factors' },
                      { key: 'environmental', title: 'Environmental Factors' },
                      { key: 'legal', title: 'Legal Factors' }
                    ].map((item, idx) => {
                      const desc = result.pestel?.[item.key] || 'Analyzing macro-environmental factor...';
                      return (
                        <GlassCard key={idx} className="border border-white/5">
                          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-white/5 pb-2 mb-2">{item.title}</h4>
                          <p className="text-xs text-gray-300 leading-relaxed">{desc}</p>
                        </GlassCard>
                      );
                    })}
                  </div>
                )}

                {/* 3. COMPETITORS */}
                {activeTab === 'competitors' && (
                  <div className="space-y-4">
                    {(Array.isArray(result.competitors) ? result.competitors : Array.isArray(result.top_competitors) ? result.top_competitors : []).map((comp, idx) => (
                      <GlassCard key={idx} className="border border-white/5 flex flex-col md:flex-row justify-between gap-6">
                        <div className="space-y-2">
                          <h4 className="text-base font-bold text-white flex items-center space-x-2">
                            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
                            <span>{comp.name}</span>
                          </h4>
                          <div className="flex space-x-4 text-xs text-gray-400">
                            <span>Market Position: <strong>{comp.market_position || 'Challenger'}</strong></span>
                            <span>Threat: <strong className="text-rose-400">{comp.threat_level || 'Medium'}</strong></span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-300 w-full md:max-w-md">
                          <div>
                            <span className="text-[10px] text-gray-500 font-bold uppercase block mb-1">Key Strengths</span>
                            <ul className="space-y-1">
                              {renderBulletList(comp.strengths)}
                            </ul>
                          </div>
                          <div>
                            <span className="text-[10px] text-gray-500 font-bold uppercase block mb-1">Key Weaknesses</span>
                            <ul className="space-y-1">
                              {renderBulletList(comp.weaknesses)}
                            </ul>
                          </div>
                        </div>
                      </GlassCard>
                    ))}
                  </div>
                )}

                {/* 4. CHARTS */}
                {activeTab === 'charts' && (
                  <GlassCard className="border border-white/5">
                    <h3 className="text-base font-bold text-white mb-6">Market Growth Trajectory (USD Billions)</h3>
                    <div className="h-80 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <defs>
                            <linearGradient id="colorSize" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.06)" />
                          <XAxis dataKey="name" stroke="rgba(15, 23, 42, 0.4)" fontSize={11} />
                          <YAxis stroke="rgba(15, 23, 42, 0.4)" fontSize={11} />
                          <Tooltip 
                            contentStyle={{ 
                              background: 'rgba(255, 255, 255, 0.95)', 
                              border: '1px solid rgba(15, 23, 42, 0.08)', 
                              borderRadius: '12px',
                              boxShadow: '0 4px 12px rgba(15, 23, 42, 0.05)'
                            }}
                            itemStyle={{ color: '#0f172a' }}
                            labelStyle={{ color: '#64748b', fontWeight: 'bold' }}
                          />
                          <Area type="monotone" dataKey="Size" stroke="#0ea5e9" strokeWidth={2} fillOpacity={1} fill="url(#colorSize)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </GlassCard>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <ChatAssistant domain="market" contextData={result} getCsrfToken={getCsrfToken} />
    </div>
  );
}
