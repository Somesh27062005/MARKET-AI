import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  DollarSign, 
  Users, 
  Percent, 
  Activity, 
  ArrowUpRight, 
  ArrowDownRight, 
  ChevronRight, 
  Cpu, 
  Sparkles,
  TrendingUp
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar 
} from 'recharts';
import GlassCard from '../components/GlassCard.jsx';
import ChatAssistant from '../components/ChatAssistant.jsx';

const COLORS = ['#6366f1', '#0ea5e9', '#10b981'];

export default function Dashboard({ getCsrfToken }) {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const statsRes = await fetch('/api/dashboard/stats');
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }

        const summaryRes = await fetch('/api/dashboard/executive-summary');
        if (summaryRes.ok) {
          const summaryData = await summaryRes.json();
          setSummary(summaryData);
        }
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
        setSummaryLoading(false);
      }
    }

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400 font-medium">Analyzing business metrics...</p>
        </div>
      </div>
    );
  }

  const { stats: statsObj, has_real_data, company_metrics } = stats || {};

  // Formulating chart data from API
  const salesTrendData = (statsObj?.sales_trend || []).map((val, idx) => ({
    name: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][idx] || `M${idx + 1}`,
    Revenue: val
  }));

  const leadDistData = [
    { name: 'Hot Leads', value: statsObj?.lead_distribution?.[0] || 0 },
    { name: 'Warm Leads', value: statsObj?.lead_distribution?.[1] || 0 },
    { name: 'Cold Leads', value: statsObj?.lead_distribution?.[2] || 0 },
  ].filter(d => d.value > 0);

  const campaignClickData = (statsObj?.campaign_clicks || []).map((val, idx) => ({
    name: ['LinkedIn', 'Facebook', 'Google Ads', 'Email', 'Twitter/X', 'YouTube'][idx] || `Ch${idx + 1}`,
    Clicks: val
  }));

  // Derive chart empty-state flags
  const salesTrendHasData = salesTrendData.some(d => d.Revenue > 0);
  const channelHasData    = campaignClickData.some(d => d.Clicks > 0);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Upper header summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Business Overview</h1>
          <p className="text-gray-400 mt-1">Real-time performance metrics and AI intelligence feedback.</p>
        </div>
        <div className="flex items-center space-x-3">
          <span className={`text-xs font-semibold px-3 py-1.5 rounded-full border ${has_real_data ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-400' : 'bg-yellow-600/10 border-yellow-500/20 text-yellow-400'}`}>
            {has_real_data ? '⚡ Real Corporate Feed' : '🔧 Demo Simulation Feed'}
          </span>
          {!has_real_data && (
            <button 
              onClick={() => navigate('/profile')}
              className="text-xs font-medium text-white hover:text-indigo-300 bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-xl transition-all"
            >
              Connect Real metrics
            </button>
          )}
        </div>
      </div>

      {/* KPI Counters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {/* Total Revenue */}
        <GlassCard className="flex items-center space-x-5" interactive>
          <div className="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Aggregate Revenue</span>
            <h3 className="text-2xl font-display font-bold text-white mt-1">
              ${(statsObj?.total_revenue || 0).toLocaleString()}
            </h3>
            <div className="flex items-center text-xs text-emerald-400 font-semibold mt-1">
              <ArrowUpRight className="w-3.5 h-3.5 mr-1" />
              <span>+14.2% MoM</span>
            </div>
          </div>
        </GlassCard>

        {/* Total Leads */}
        <GlassCard className="flex items-center space-x-5" interactive>
          <div className="w-12 h-12 rounded-xl bg-cyan-600/20 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Captured Leads</span>
            <h3 className="text-2xl font-display font-bold text-white mt-1">
              {(statsObj?.total_leads || 0).toLocaleString()}
            </h3>
            <div className="flex items-center text-xs text-emerald-400 font-semibold mt-1">
              <ArrowUpRight className="w-3.5 h-3.5 mr-1" />
              <span>+8.4% weekly</span>
            </div>
          </div>
        </GlassCard>

        {/* Hot Leads */}
        <GlassCard className="flex items-center space-x-5" interactive>
          <div className="w-12 h-12 rounded-xl bg-emerald-600/20 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Activity className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Hot Leads Qualified</span>
            <h3 className="text-2xl font-display font-bold text-white mt-1">
              {statsObj?.hot_leads || 0}
            </h3>
            <div className="flex items-center text-xs text-indigo-400 font-semibold mt-1">
              <span>{Math.round(((statsObj?.hot_leads || 0) / (statsObj?.total_leads || 1)) * 100)}% Conversion rate</span>
            </div>
          </div>
        </GlassCard>

        {/* Average Lead Score */}
        <GlassCard className="flex items-center space-x-5" interactive>
          <div className="w-12 h-12 rounded-xl bg-yellow-600/20 border border-yellow-500/20 flex items-center justify-center text-yellow-400">
            <Percent className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Avg Qualification Score</span>
            <h3 className="text-2xl font-display font-bold text-white mt-1">
              {statsObj?.avg_lead_score || 0}/100
            </h3>
            <div className="flex items-center text-xs text-gray-500 mt-1">
              <span>Dynamic BANT standard</span>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* AI Advisor Executive Summary Box */}
      <GlassCard className="border border-indigo-500/10 bg-indigo-950/10 relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -right-20 -top-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex items-center space-x-2 border-b border-indigo-500/10 pb-3 mb-4">
          <Cpu className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">MarketMind AI Executive Advisor</h2>
        </div>

        {summaryLoading ? (
          <div className="flex items-center space-x-3 py-2 text-sm text-gray-400">
            <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <span>Generating advisory analysis...</span>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-300 leading-relaxed font-medium">
              {summary?.summary || "Advisory summary loading..."}
            </p>
            {summary?.highlights && summary.highlights.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {summary.highlights.map((h, i) => (
                  <span key={i} className="text-xs font-semibold px-3 py-1 rounded-xl bg-indigo-950/40 border border-indigo-500/10 text-indigo-300 flex items-center space-x-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{h}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </GlassCard>

      {/* Charts Block */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Sales Trend Chart */}
        <GlassCard className="xl:col-span-2 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-white">Monthly Sales Pipeline Revenue</h2>
              <span className="text-xs text-gray-400">12-month rolling summary</span>
            </div>
            <TrendingUp className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="h-80 w-full">
            {!salesTrendHasData ? (
              <div className="h-full flex flex-col items-center justify-center space-y-3 text-center">
                <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/10 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">No revenue data yet</p>
                  <p className="text-xs text-gray-500 mt-1 max-w-xs">Add your Monthly Revenue in <button onClick={() => navigate('/profile')} className="text-indigo-400 hover:underline">Settings → Sales & Marketing KPIs</button> to see your trend.</p>
                </div>
              </div>
            ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={salesTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.06)" />
                <XAxis dataKey="name" stroke="rgba(15, 23, 42, 0.4)" fontSize={11} />
                <YAxis stroke="rgba(15, 23, 42, 0.4)" fontSize={11} tickFormatter={(v) => v >= 1000 ? `$${(v/1000).toFixed(0)}k` : `$${v}`} />
                <Tooltip 
                  contentStyle={{ 
                    background: 'rgba(255, 255, 255, 0.95)', 
                    border: '1px solid rgba(15, 23, 42, 0.08)', 
                    borderRadius: '12px',
                    boxShadow: '0 4px 12px rgba(15, 23, 42, 0.05)'
                  }}
                  itemStyle={{ color: '#0f172a' }}
                  labelStyle={{ color: '#64748b', fontWeight: 'bold' }}
                  formatter={(v) => [`$${Number(v).toLocaleString()}`, 'Revenue']}
                />
                <Area type="monotone" dataKey="Revenue" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
              </AreaChart>
            </ResponsiveContainer>
            )}
          </div>
        </GlassCard>

        {/* Lead Share distribution */}
        <GlassCard className="flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-white mb-1">Lead Share Distribution</h2>
            <span className="text-xs text-gray-400">Qualified database split</span>
          </div>
          <div className="h-56 relative flex items-center justify-center my-4">
            {leadDistData.length === 0 ? (
              <span className="text-xs text-gray-500">No leads qualified in CRM.</span>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={leadDistData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {leadDistData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      background: 'rgba(255, 255, 255, 0.95)', 
                      border: '1px solid rgba(15, 23, 42, 0.08)', 
                      borderRadius: '12px', 
                      boxShadow: '0 4px 12px rgba(15, 23, 42, 0.05)',
                      fontSize: '11px' 
                    }}
                    itemStyle={{ color: '#0f172a' }}
                    labelStyle={{ color: '#64748b', fontWeight: 'bold' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
            {/* Center label */}
            <div className="absolute flex flex-col items-center">
              <span className="text-2xl font-bold text-white font-display">
                {statsObj?.total_leads || 0}
              </span>
              <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">Total Leads</span>
            </div>
          </div>
          {/* Legend */}
          <div className="space-y-2.5">
            {leadDistData.map((item, idx) => (
              <div key={item.name} className="flex items-center justify-between text-xs border-b border-white/5 pb-2 last:border-0 last:pb-0">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                  <span className="text-gray-400">{item.name}</span>
                </div>
                <span className="text-white font-semibold">{item.value} leads</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Lower Row Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Campaign Click Volume Chart */}
        <GlassCard className="xl:col-span-2 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-white">Acquisition Channel Click Performance</h2>
              <span className="text-xs text-gray-400">Total click-through traffic split</span>
            </div>
            <Users className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="h-64 w-full">
            {!channelHasData ? (
              <div className="h-full flex flex-col items-center justify-center space-y-3 text-center">
                <div className="w-12 h-12 rounded-2xl bg-cyan-600/10 border border-cyan-500/10 flex items-center justify-center">
                  <Users className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">No campaign data yet</p>
                  <p className="text-xs text-gray-500 mt-1 max-w-xs">Set your <button onClick={() => navigate('/profile')} className="text-indigo-400 hover:underline">Top Channel & Active Campaigns</button> in Settings, or run your first campaign.</p>
                </div>
              </div>
            ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={campaignClickData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                <Bar dataKey="Clicks" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            )}
          </div>
        </GlassCard>

        {/* Quick Launch Panel */}
        <GlassCard className="flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-white mb-1">AI Action Center</h2>
            <span className="text-xs text-gray-400">Instantly execute workflows</span>
          </div>
          
          <div className="space-y-3 my-4 flex-1 flex flex-col justify-center">
            {[
              { title: 'Create Ad Campaign', desc: 'Generate high-ROI marketing copies.', path: '/campaigns' },
              { title: 'Personalize Pitch', desc: 'Craft high-converting elevator pitch.', path: '/pitch' },
              { title: 'Score Incoming Lead', desc: 'Qualify buyer interest via BANT.', path: '/leads' },
            ].map((action, i) => (
              <button
                key={i}
                onClick={() => navigate(action.path)}
                className="w-full text-left p-3.5 rounded-xl border border-white/5 hover:border-indigo-500/20 bg-white/2 hover:bg-white/5 transition-all flex items-center justify-between group"
              >
                <div>
                  <h4 className="text-sm font-semibold text-white group-hover:text-indigo-400 transition-colors">{action.title}</h4>
                  <p className="text-[11px] text-gray-400 mt-1">{action.desc}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-white transition-colors" />
              </button>
            ))}
          </div>

          <div className="text-[11px] text-gray-500 text-center border-t border-white/5 pt-3">
            MarketMind platform compiles models using Groq LLaMA 3.3.
          </div>
        </GlassCard>
      </div>
      <ChatAssistant domain="dashboard" contextData={statsObj} getCsrfToken={getCsrfToken} />
    </div>
  );
}
