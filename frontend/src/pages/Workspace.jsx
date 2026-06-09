import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  Sparkles, 
  Calculator, 
  TrendingUp, 
  HelpCircle,
  TrendingDown,
  CheckCircle,
  Activity,
  AlertTriangle,
  Play,
  Gauge
} from 'lucide-react';
import { 
  Radar, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import GlassCard from '../components/GlassCard.jsx';

export default function Workspace({ getCsrfToken }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState('sizing');
  const [dealModifier, setDealModifier] = useState(1.0);
  const [cycleModifier, setCycleModifier] = useState(1.0);
  const [simulationData, setSimulationData] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // Form inputs for market analysis
  const [industry, setIndustry] = useState('');
  const [subIndustry, setSubIndustry] = useState('');
  const [geoMarket, setGeoMarket] = useState('');
  const [competitorsText, setCompetitorsText] = useState('');

  const fetchWorkspaceSummary = async () => {
    try {
      const res = await fetch('/api/v2/market/summary');
      if (res.ok) {
        const summary = await res.json();
        setData(summary);
        // Pre-fill inputs if available
        if (summary.workspace) {
          setIndustry(summary.workspace.industry || '');
          setSubIndustry(summary.workspace.sub_industry || '');
          setGeoMarket(summary.workspace.geo_market || '');
        }
      }
    } catch (err) {
      console.error("Workspace summary fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaceSummary();
  }, []);

  const handleRunAnalysis = async (e) => {
    e.preventDefault();
    setAnalyzing(true);
    try {
      const res = await fetch('/api/v2/market/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          industry,
          product_category: subIndustry,
          target_market: geoMarket,
          competitors: competitorsText
        })
      });

      if (res.ok) {
        await fetchWorkspaceSummary();
        alert('Enterprise analysis compiled successfully!');
      }
    } catch (err) {
      console.error("Analysis failed:", err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSimulate = async () => {
    setSimulating(true);
    try {
      const res = await fetch('/api/v2/market/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          avg_deal_size_modifier: dealModifier,
          sales_cycle_days_modifier: cycleModifier
        })
      });

      if (res.ok) {
        const simRes = await res.json();
        setSimulationData(simRes);
      }
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setSimulating(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400 font-medium">Loading Enterprise Workspace...</p>
        </div>
      </div>
    );
  }

  const { workspace, market_size, competitors, opportunities, recommendations, radar_data } = data || {};

  // Formulate competitor radar data
  const chartRadarData = (radar_data || []).map(d => ({
    subject: d.metric,
    ...d.scores
  }));

  // Compiling list of competitor names for radar legend
  const competitorKeys = competitors?.map(c => c.name) || [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Enterprise Analyzer</h1>
          <p className="text-gray-400 mt-1">Simulate corporate growth, track TAM sizing, and evaluate competitors.</p>
        </div>

        <div className="flex items-center space-x-2">
          {['sizing', 'competitors', 'opportunities', 'simulation'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveSubTab(tab)}
              className={`text-xs font-semibold px-4 py-2 rounded-xl border transition-all capitalize
                ${activeSubTab === tab 
                  ? 'bg-indigo-600/20 border-indigo-500/20 text-indigo-300' 
                  : 'bg-white/5 border-white/5 text-gray-400 hover:text-white'}`}
            >
              {tab === 'sizing' && 'TAM/SAM/SOM Sizing'}
              {tab === 'competitors' && 'Competitive Radar'}
              {tab === 'opportunities' && 'Opportunity Matrix'}
              {tab === 'simulation' && 'Growth Simulator'}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 items-start">
        {/* Left side analysis run */}
        <GlassCard className="xl:col-span-1 border border-white/5">
          <div className="flex items-center space-x-2 border-b border-white/5 pb-3 mb-6">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Workspace Context</h2>
          </div>

          <form onSubmit={handleRunAnalysis} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Workspace Industry</label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Cybersecurity Services"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Sub-Industry / Category</label>
              <input
                type="text"
                value={subIndustry}
                onChange={(e) => setSubIndustry(e.target.value)}
                placeholder="e.g. Identity Access Management"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Geographic Market</label>
              <input
                type="text"
                value={geoMarket}
                onChange={(e) => setGeoMarket(e.target.value)}
                placeholder="e.g. Western Europe & NA"
                className="w-full glass-input"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">List Competitors (Comma-separated)</label>
              <textarea
                value={competitorsText}
                onChange={(e) => setCompetitorsText(e.target.value)}
                placeholder="e.g. Okta, Ping Identity, ForgeRock"
                rows="2"
                className="w-full glass-input"
              ></textarea>
            </div>

            <button
              type="submit"
              disabled={analyzing}
              className="w-full glass-button-primary flex items-center justify-center space-x-2 py-2.5 disabled:opacity-50"
            >
              {analyzing ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Layers className="w-4 h-4" />
                  <span>Update Workspace Summary</span>
                </>
              )}
            </button>
          </form>
        </GlassCard>

        {/* Right side tab outputs */}
        <div className="xl:col-span-2 space-y-6">
          {/* TAB 1: SIZING */}
          {activeSubTab === 'sizing' && (
            <div className="space-y-6">
              {/* Sizing values cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  { label: 'TAM (Total Addressable Market)', val: market_size?.tam, color: 'text-indigo-400 bg-indigo-500/5 border-indigo-500/10' },
                  { label: 'SAM (Serviceable Addressable)', val: market_size?.sam, color: 'text-cyan-400 bg-cyan-500/5 border-cyan-500/10' },
                  { label: 'SOM (Serviceable Obtainable)', val: market_size?.som, color: 'text-emerald-400 bg-emerald-500/5 border-emerald-500/10' }
                ].map((sCard, i) => (
                  <GlassCard key={i} className={`border p-5 ${sCard.color}`}>
                    <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold block">{sCard.label}</span>
                    <h3 className="text-xl font-display font-bold text-white mt-2">
                      {sCard.val ? `$${sCard.val.toLocaleString()}` : '$0.00'}
                    </h3>
                  </GlassCard>
                ))}
              </div>

              {/* Sizing Details */}
              <GlassCard className="border border-white/5 space-y-4">
                <div className="flex items-center space-x-2 border-b border-white/5 pb-2 mb-2">
                  <Calculator className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">Market CAGR & Documentation</h3>
                </div>
                <div className="text-xs text-gray-300 space-y-3">
                  <p>
                    <strong>Annual Growth Rate (CAGR):</strong> {market_size?.growth_rate_cagr ? `${market_size.growth_rate_cagr}%` : 'N/A'}
                  </p>
                  {market_size?.source_documentation && (
                    <div className="bg-white/2 p-3 rounded-lg border border-white/5">
                      <h4 className="font-semibold text-white mb-1">Source Documentation / Context</h4>
                      <p className="text-gray-400 leading-relaxed italic">"{market_size.source_documentation}"</p>
                    </div>
                  )}
                </div>
              </GlassCard>
            </div>
          )}

          {/* TAB 2: COMPETITORS RADAR */}
          {activeSubTab === 'competitors' && (
            <GlassCard className="border border-white/5 flex flex-col justify-between">
              <div>
                <h3 className="text-base font-bold text-white mb-1">Competitor Capability Matrix</h3>
                <span className="text-xs text-gray-400">Scorecard evaluation across core reach and quality metrics</span>
              </div>

              {chartRadarData.length === 0 ? (
                <div className="h-64 flex items-center justify-center text-xs text-gray-500">
                  Execute "Update Workspace Summary" on the left to generate competitor radar metrics.
                </div>
              ) : (
                <div className="h-80 w-full my-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartRadarData}>
                      <PolarGrid stroke="rgba(255,255,255,0.05)" />
                      <PolarAngleAxis dataKey="subject" stroke="rgba(255,255,255,0.4)" fontSize={11} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="rgba(255,255,255,0.2)" fontSize={9} />
                      {competitorKeys.slice(0, 3).map((compName, cIdx) => {
                        const radarColors = ['#6366f1', '#0ea5e9', '#10b981'];
                        return (
                          <Radar
                            key={compName}
                            name={compName}
                            dataKey={compName}
                            stroke={radarColors[cIdx % radarColors.length]}
                            fill={radarColors[cIdx % radarColors.length]}
                            fillOpacity={0.15}
                          />
                        );
                      })}
                      <Legend verticalAlign="bottom" height={36} />
                      <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </GlassCard>
          )}

          {/* TAB 3: OPPORTUNITIES MATRIX */}
          {activeSubTab === 'opportunities' && (
            <div className="space-y-6">
              <GlassCard className="border border-white/5">
                <h3 className="text-base font-bold text-white mb-4">Discovered Market Opportunities</h3>
                <div className="space-y-3">
                  {!Array.isArray(opportunities) || opportunities.length === 0 ? (
                    <p className="text-xs text-gray-500 text-center py-4">No opportunities discovered. Run workspace summary update.</p>
                  ) : (
                    opportunities.map((opp) => (
                      <div key={opp.id} className="bg-white/2 p-4 rounded-xl border border-white/5 text-xs flex justify-between items-start gap-4">
                        <div className="space-y-1">
                          <h4 className="font-bold text-white text-sm">{opp.title}</h4>
                          <p className="text-gray-400">{opp.description}</p>
                          {opp.estimated_revenue && <span className="text-[10px] text-emerald-400 font-bold block pt-1">Potential Value: ${(opp.estimated_revenue).toLocaleString()}</span>}
                        </div>
                        <span className="bg-indigo-500/10 text-indigo-400 px-2 py-1 rounded text-[10px] uppercase font-bold shrink-0">
                          Priority: {opp.impact_score}/10
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </GlassCard>

              {/* Strategic Recs */}
              <GlassCard className="border border-white/5">
                <h3 className="text-base font-bold text-white mb-4">Strategic Recommendations</h3>
                <div className="space-y-3">
                  {!Array.isArray(recommendations) || recommendations.length === 0 ? (
                    <p className="text-xs text-gray-500 text-center py-4">No strategic recommendations logged yet.</p>
                  ) : (
                    recommendations.map((rec) => (
                      <div key={rec.id} className="bg-white/2 p-3.5 rounded-xl border border-white/5 text-xs">
                        <div className="flex justify-between font-bold text-white mb-1.5">
                          <span>{rec.title}</span>
                          <span className={`text-[10px] uppercase px-2 py-0.5 rounded ${rec.priority === 'High' ? 'bg-rose-500/10 text-rose-400' : 'bg-white/5 text-gray-400'}`}>
                            {rec.priority}
                          </span>
                        </div>
                        <p className="text-gray-400">{rec.description}</p>
                      </div>
                    ))
                  )}
                </div>
              </GlassCard>
            </div>
          )}

          {/* TAB 4: SIMULATOR */}
          {activeSubTab === 'simulation' && (
            <div className="space-y-6">
              {/* Slider Inputs */}
              <GlassCard className="border border-white/5 space-y-6">
                <div>
                  <h3 className="text-base font-bold text-white mb-1 flex items-center space-x-2">
                    <Gauge className="w-5 h-5 text-indigo-400 animate-pulse" />
                    <span>Dynamic Projections Simulator</span>
                  </h3>
                  <span className="text-xs text-gray-400">Modify operational parameters to simulate 12-month growth output.</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  {/* Deal Size Slider */}
                  <div className="space-y-2">
                    <div className="flex justify-between font-bold text-white">
                      <span>Average Deal Size Modifier</span>
                      <span className="text-indigo-400 font-mono">{dealModifier.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="2.5"
                      step="0.1"
                      value={dealModifier}
                      onChange={(e) => setDealModifier(parseFloat(e.target.value))}
                      className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                    <div className="flex justify-between text-[9px] text-gray-500">
                      <span>0.5x deal shrinkage</span>
                      <span>2.5x deal scaling</span>
                    </div>
                  </div>

                  {/* Cycle Days Slider */}
                  <div className="space-y-2">
                    <div className="flex justify-between font-bold text-white">
                      <span>Sales Cycle Duration Modifier</span>
                      <span className="text-indigo-400 font-mono">{cycleModifier.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="2.5"
                      step="0.1"
                      value={cycleModifier}
                      onChange={(e) => setCycleModifier(parseFloat(e.target.value))}
                      className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                    <div className="flex justify-between text-[9px] text-gray-500">
                      <span>0.5x faster velocity</span>
                      <span>2.5x longer cycle</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleSimulate}
                  disabled={simulating}
                  className="w-full glass-button-primary flex items-center justify-center space-x-2 py-2 text-xs font-semibold"
                >
                  {simulating ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <>
                      <Play className="w-4.5 h-4.5" />
                      <span>Run Growth Simulation Projections</span>
                    </>
                  )}
                </button>
              </GlassCard>

              {/* Simulation Output Projections */}
              {simulationData && (
                <GlassCard className="border border-white/5 space-y-6">
                  {/* Results highlight cards */}
                  <div className="grid grid-cols-3 gap-4 border-b border-white/5 pb-4">
                    <div className="text-center bg-white/2 p-3 rounded-xl">
                      <span className="text-[10px] text-gray-500 uppercase block">Growth Multiplier</span>
                      <span className="text-base font-bold text-white block mt-1">{simulationData.growth_multiplier}x</span>
                    </div>
                    <div className="text-center bg-white/2 p-3 rounded-xl">
                      <span className="text-[10px] text-gray-500 uppercase block">12M Baseline SOM</span>
                      <span className="text-base font-bold text-gray-400 block mt-1">${(simulationData.baseline_projection_12m).toLocaleString()}</span>
                    </div>
                    <div className="text-center bg-white/2 p-3 rounded-xl border border-indigo-500/10 bg-indigo-950/10">
                      <span className="text-[10px] text-indigo-400 uppercase block">12M Simulated Proj</span>
                      <span className="text-base font-bold text-indigo-300 block mt-1">${(simulationData.simulated_projection_12m).toLocaleString()}</span>
                    </div>
                  </div>

                  {/* Growth chart */}
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-4">12-Month Projections Comparison</h4>
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={simulationData.simulation_chart} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                          <XAxis dataKey="month" stroke="rgba(255,255,255,0.3)" fontSize={11} />
                          <YAxis stroke="rgba(255,255,255,0.3)" fontSize={11} tickFormatter={(v) => `$${v/1000}k`} />
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                          <Tooltip 
                            contentStyle={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                          />
                          <Legend />
                          <Area name="Baseline projection" type="monotone" dataKey="baseline" stroke="rgba(255,255,255,0.2)" fill="rgba(255,255,255,0.02)" />
                          <Area name="Simulated Proj" type="monotone" dataKey="simulated" stroke="#6366f1" fill="rgba(99, 102, 241, 0.08)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </GlassCard>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
