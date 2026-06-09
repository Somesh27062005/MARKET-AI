import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Sparkles, 
  Save, 
  HelpCircle,
  Building,
  DollarSign,
  UserCheck,
  TrendingUp,
  Percent,
  Compass
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';

export default function Profile({ user, setUser, getCsrfToken }) {
  const [activeTab, setActiveTab] = useState('company');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // 1. Company Profile State
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [subIndustry, setSubIndustry] = useState('');
  const [companySize, setCompanySize] = useState('10-50 employees');
  const [website, setWebsite] = useState('');
  const [description, setDescription] = useState('');
  const [hqCountry, setHqCountry] = useState('');
  const [geoMarket, setGeoMarket] = useState('');
  const [businessModel, setBusinessModel] = useState('');
  const [targetCustomer, setTargetCustomer] = useState('');
  const [foundedYear, setFoundedYear] = useState('');
  
  // 2. KPIs State
  const [monthlyRevenue, setMonthlyRevenue] = useState(0);
  const [revenueTarget, setRevenueTarget] = useState(0);
  const [monthlyLeads, setMonthlyLeads] = useState(0);
  const [leadTarget, setLeadTarget] = useState(0);
  const [activeCampaigns, setActiveCampaigns] = useState(0);
  const [conversionRate, setConversionRate] = useState(0);
  const [avgDealSize, setAvgDealSize] = useState(0);
  const [salesCycleDays, setSalesCycleDays] = useState(0);
  const [topChannel, setTopChannel] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [salesTeamSize, setSalesTeamSize] = useState(0);
  const [winRate, setWinRate] = useState(0);
  const [cac, setCac] = useState(0);
  const [ltv, setLtv] = useState(0);
  
  // 3. ICP State
  const [icpIndustry, setIcpIndustry] = useState('');
  const [icpCompanySize, setIcpCompanySize] = useState('');
  const [icpRevenueRange, setIcpRevenueRange] = useState('');
  const [icpJobTitles, setIcpJobTitles] = useState(''); // comma-separated strings
  const [icpDecisionMakers, setIcpDecisionMakers] = useState(''); // comma-separated strings
  const [icpPainPoints, setIcpPainPoints] = useState(''); // comma-separated strings
  const [icpNotes, setIcpNotes] = useState('');

  const fetchProfileData = async () => {
    try {
      // Load onboarding profile
      const profRes = await fetch('/api/onboarding/profile');
      if (profRes.ok) {
        const profData = await profRes.json();
        const biz = profData.profile || {};
        setCompanyName(biz.company_name || '');
        setIndustry(biz.industry || '');
        setSubIndustry(biz.sub_industry || '');
        setCompanySize(biz.company_size || '10-50 employees');
        setWebsite(biz.website || '');
        setDescription(biz.description || '');
        setHqCountry(biz.hq_country || '');
        setGeoMarket(biz.geo_market || '');
        setBusinessModel(biz.business_model || '');
        setTargetCustomer(biz.target_customer || '');
        setFoundedYear(biz.founded_year || '');
      }

      // Load company KPIs
      const kpiRes = await fetch('/api/company-metrics');
      if (kpiRes.ok) {
        const kpiData = await kpiRes.json();
        const metrics = kpiData.metrics || {};
        setMonthlyRevenue(metrics.monthly_revenue || 0);
        setRevenueTarget(metrics.revenue_target || 0);
        setMonthlyLeads(metrics.monthly_leads || 0);
        setLeadTarget(metrics.lead_target || 0);
        setActiveCampaigns(metrics.active_campaigns || 0);
        setConversionRate(metrics.conversion_rate || 0);
        setAvgDealSize(metrics.avg_deal_size || 0);
        setSalesCycleDays(metrics.sales_cycle_days || 0);
        setTopChannel(metrics.top_channel || '');
        setCurrency(metrics.currency || 'USD');
        setSalesTeamSize(metrics.sales_team_size || 0);
        setWinRate(metrics.win_rate || 0);
        setCac(metrics.cac || 0);
        setLtv(metrics.ltv || 0);
      }

      // Load ICP Details
      const icpRes = await fetch('/api/icp');
      if (icpRes.ok) {
        const icpData = await icpRes.json();
        const icp = icpData.profile || {};
        setIcpIndustry(icp.icp_industry || '');
        setIcpCompanySize(icp.icp_company_size || '');
        setIcpRevenueRange(icp.icp_revenue_range || '');
        
        // Handle parsing arrays/JSON strings from database
        try {
          const titles = typeof icp.icp_job_titles === 'string' ? JSON.parse(icp.icp_job_titles) : icp.icp_job_titles;
          setIcpJobTitles(Array.isArray(titles) ? titles.join(', ') : '');
        } catch (e) { setIcpJobTitles(''); }

        try {
          const dm = typeof icp.icp_decision_makers === 'string' ? JSON.parse(icp.icp_decision_makers) : icp.icp_decision_makers;
          setIcpDecisionMakers(Array.isArray(dm) ? dm.join(', ') : '');
        } catch (e) { setIcpDecisionMakers(''); }

        try {
          const pp = typeof icp.icp_pain_points === 'string' ? JSON.parse(icp.icp_pain_points) : icp.icp_pain_points;
          setIcpPainPoints(Array.isArray(pp) ? pp.join(', ') : '');
        } catch (e) { setIcpPainPoints(''); }

        setIcpNotes(icp.icp_notes || '');
      }
    } catch (err) {
      console.error("Profile load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileData();
  }, []);

  const handleSaveCompany = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess('');
    setError('');

    try {
      const res = await fetch('/api/onboarding/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          business: {
            company_name: companyName,
            industry,
            sub_industry: subIndustry,
            size: companySize,
            website,
            description,
            hq_country: hqCountry,
            geo_market: geoMarket,
            business_model: businessModel,
            target_customer: targetCustomer,
            founded_year: foundedYear
          }
        })
      });

      if (res.ok) {
        setSuccess('Company profile parameters saved successfully!');
      } else {
        setError('Failed to save profile details.');
      }
    } catch (err) {
      console.error(err);
      setError('Communication error.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveKPIs = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess('');
    setError('');

    try {
      const res = await fetch('/api/company-metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          monthly_revenue: monthlyRevenue,
          revenue_target: revenueTarget,
          monthly_leads: monthlyLeads,
          lead_target: leadTarget,
          active_campaigns: activeCampaigns,
          conversion_rate: conversionRate,
          avg_deal_size: avgDealSize,
          sales_cycle_days: salesCycleDays,
          top_channel: topChannel,
          currency,
          sales_team_size: salesTeamSize,
          win_rate: winRate,
          cac,
          ltv
        })
      });

      if (res.ok) {
        setSuccess('Company business health KPIs updated successfully!');
      } else {
        setError('Failed to update KPIs.');
      }
    } catch (err) {
      console.error(err);
      setError('Network communication failed.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveICP = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess('');
    setError('');

    // Parse comma-separated strings to arrays
    const jobTitlesArr = icpJobTitles.split(',').map(s => s.trim()).filter(Boolean);
    const decisionMakersArr = icpDecisionMakers.split(',').map(s => s.trim()).filter(Boolean);
    const painPointsArr = icpPainPoints.split(',').map(s => s.trim()).filter(Boolean);

    try {
      const res = await fetch('/api/icp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          icp_industry: icpIndustry,
          icp_company_size: icpCompanySize,
          icp_revenue_range: icpRevenueRange,
          icp_job_titles: jobTitlesArr,
          icp_decision_makers: decisionMakersArr,
          icp_pain_points: painPointsArr,
          icp_notes: icpNotes
        })
      });

      if (res.ok) {
        setSuccess('Ideal Customer Profile (ICP) parameters stored successfully!');
      } else {
        setError('Failed to update ICP profile.');
      }
    } catch (err) {
      console.error(err);
      setError('Network communication failure.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Settings & KPIs</h1>
          <p className="text-gray-400 mt-1">Configure company profiles, specify corporate KPIs, and calibrate buyer ICP targets.</p>
        </div>

        <div className="flex items-center space-x-2">
          {[
            { id: 'company', label: 'Company profile', icon: Building },
            { id: 'kpis', label: 'Sales & Marketing KPIs', icon: DollarSign },
            { id: 'icp', label: 'Ideal Buyer ICP', icon: UserCheck }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setSuccess('');
                  setError('');
                }}
                className={`text-xs font-semibold px-4 py-2 rounded-xl border transition-all flex items-center space-x-1.5
                  ${activeTab === tab.id 
                    ? 'bg-indigo-600/20 border-indigo-500/20 text-indigo-300' 
                    : 'bg-white/5 border-white/5 text-gray-400 hover:text-white'}`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-sm text-emerald-400 font-medium max-w-4xl">
          {success}
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 text-sm text-rose-400 font-medium max-w-4xl">
          {error}
        </div>
      )}

      {loading ? (
        <div className="h-48 flex items-center justify-center">
          <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="max-w-4xl">
          {/* TAB 1: COMPANY PROFILE */}
          {activeTab === 'company' && (
            <GlassCard className="border border-white/5">
              <form onSubmit={handleSaveCompany} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Name</label>
                    <input
                      type="text"
                      required
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="w-full glass-input"
                      placeholder="e.g. Acme Corp"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Primary Industry Sector</label>
                    <input
                      type="text"
                      required
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      className="w-full glass-input"
                      placeholder="e.g. Technology, Supply Chain"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Sub-Industry / Category</label>
                    <input
                      type="text"
                      value={subIndustry}
                      onChange={(e) => setSubIndustry(e.target.value)}
                      className="w-full glass-input"
                      placeholder="e.g. Identity Access Management"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Company Size</label>
                    <select
                      value={companySize}
                      onChange={(e) => setCompanySize(e.target.value)}
                      className="w-full glass-input"
                    >
                      <option value="1-10 employees">1 – 10 employees</option>
                      <option value="10-50 employees">10 – 50 employees</option>
                      <option value="50-250 employees">50 – 250 employees</option>
                      <option value="250-1000 employees">250 – 1000 employees</option>
                      <option value="1000+ employees">1,000+ employees</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Website</label>
                    <input
                      type="url"
                      value={website}
                      onChange={(e) => setWebsite(e.target.value)}
                      className="w-full glass-input"
                      placeholder="https://company.com"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Headquarters Country</label>
                    <input
                      type="text"
                      value={hqCountry}
                      onChange={(e) => setHqCountry(e.target.value)}
                      className="w-full glass-input"
                      placeholder="e.g. United States"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Geographic Target Markets</label>
                    <input
                      type="text"
                      value={geoMarket}
                      onChange={(e) => setGeoMarket(e.target.value)}
                      className="w-full glass-input"
                      placeholder="e.g. North America, APAC"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Founded Year</label>
                    <input
                      type="text"
                      value={foundedYear}
                      onChange={(e) => setFoundedYear(e.target.value)}
                      className="w-full glass-input"
                      placeholder="e.g. 2021"
                    />
                  </div>
                </div>

                <div className="text-xs">
                  <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Business Model</label>
                  <select
                    value={businessModel}
                    onChange={(e) => setBusinessModel(e.target.value)}
                    className="w-full glass-input"
                  >
                    <option value="">Select Business Model</option>
                    <option value="B2B">B2B (Business to Business)</option>
                    <option value="B2C">B2C (Business to Consumer)</option>
                    <option value="B2B2C">B2B2C (Business to Business to Consumer)</option>
                    <option value="D2C">D2C (Direct to Consumer)</option>
                    <option value="Marketplace">Marketplace (Marketplace / Platform)</option>
                  </select>
                </div>

                <div className="text-xs">
                  <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Brief Company Description</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows="3"
                    className="w-full glass-input"
                    placeholder="Describe your core product offerings, target buyers, and key differentiation points..."
                  ></textarea>
                </div>

                <button
                  type="submit"
                  disabled={saving}
                  className="glass-button-primary flex items-center justify-center space-x-2 px-5 py-2.5 text-xs font-semibold disabled:opacity-40"
                >
                  <Save className="w-4 h-4" />
                  <span>Save Profile Parameters</span>
                </button>
              </form>
            </GlassCard>
          )}

          {/* TAB 2: KPIs */}
          {activeTab === 'kpis' && (
            <GlassCard className="border border-white/5">
              <form onSubmit={handleSaveKPIs} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Revenue (Base)</label>
                    <input
                      type="number"
                      value={monthlyRevenue}
                      onChange={(e) => setMonthlyRevenue(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Revenue Target</label>
                    <input
                      type="number"
                      value={revenueTarget}
                      onChange={(e) => setRevenueTarget(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Leads volume</label>
                    <input
                      type="number"
                      value={monthlyLeads}
                      onChange={(e) => setMonthlyLeads(parseInt(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Leads Target</label>
                    <input
                      type="number"
                      value={leadTarget}
                      onChange={(e) => setLeadTarget(parseInt(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Sales Cycle Duration (Days)</label>
                    <input
                      type="number"
                      value={salesCycleDays}
                      onChange={(e) => setSalesCycleDays(parseInt(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Average Deal Size (USD)</label>
                    <input
                      type="number"
                      value={avgDealSize}
                      onChange={(e) => setAvgDealSize(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Acquisition Cost (CAC)</label>
                    <input
                      type="number"
                      value={cac}
                      onChange={(e) => setCac(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Customer Lifetime Value (LTV)</label>
                    <input
                      type="number"
                      value={ltv}
                      onChange={(e) => setLtv(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Lead Conversion Rate (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={conversionRate}
                      onChange={(e) => setConversionRate(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Sales Win Rate (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={winRate}
                      onChange={(e) => setWinRate(parseFloat(e.target.value))}
                      className="w-full glass-input"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={saving}
                  className="glass-button-primary flex items-center justify-center space-x-2 px-5 py-2.5 text-xs font-semibold disabled:opacity-40"
                >
                  <Save className="w-4 h-4" />
                  <span>Update Dashboard KPIs</span>
                </button>
              </form>
            </GlassCard>
          )}

          {/* TAB 3: ICP */}
          {activeTab === 'icp' && (
            <GlassCard className="border border-white/5">
              <form onSubmit={handleSaveICP} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Industry Sector</label>
                    <input
                      type="text"
                      value={icpIndustry}
                      onChange={(e) => setIcpIndustry(e.target.value)}
                      placeholder="e.g. Retail, FinTech"
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Company Size</label>
                    <input
                      type="text"
                      value={icpCompanySize}
                      onChange={(e) => setIcpCompanySize(e.target.value)}
                      placeholder="e.g. 500-1000 employees"
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Revenue Range</label>
                    <input
                      type="text"
                      value={icpRevenueRange}
                      onChange={(e) => setIcpRevenueRange(e.target.value)}
                      placeholder="e.g. $20M – $100M ARR"
                      className="w-full glass-input"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Job Titles (Comma-separated)</label>
                    <input
                      type="text"
                      value={icpJobTitles}
                      onChange={(e) => setIcpJobTitles(e.target.value)}
                      placeholder="e.g. VP Operations, Chief Information Officer"
                      className="w-full glass-input"
                    />
                  </div>
                </div>

                <div className="text-xs">
                  <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Decision Maker Personas (Comma-separated)</label>
                  <input
                    type="text"
                    value={icpDecisionMakers}
                    onChange={(e) => setIcpDecisionMakers(e.target.value)}
                    placeholder="e.g. VP Engineering, Security Director"
                    className="w-full glass-input"
                  />
                </div>

                <div className="text-xs">
                  <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Target ICP Pain Points (Comma-separated)</label>
                  <textarea
                    value={icpPainPoints}
                    onChange={(e) => setIcpPainPoints(e.target.value)}
                    rows="2"
                    className="w-full glass-input"
                    placeholder="e.g. high SaaS stack overhead, slow developer onboarding"
                  ></textarea>
                </div>

                <div className="text-xs">
                  <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">ICP Account Notes</label>
                  <textarea
                    value={icpNotes}
                    onChange={(e) => setIcpNotes(e.target.value)}
                    rows="3"
                    className="w-full glass-input"
                    placeholder="Enter additional parameters or grounding guidance for target account profiling..."
                  ></textarea>
                </div>

                <button
                  type="submit"
                  disabled={saving}
                  className="glass-button-primary flex items-center justify-center space-x-2 px-5 py-2.5 text-xs font-semibold disabled:opacity-40"
                >
                  <Save className="w-4 h-4" />
                  <span>Update Buyer ICP Details</span>
                </button>
              </form>
            </GlassCard>
          )}
        </div>
      )}
    </div>
  );
}
