import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Settings, 
  Sparkles, 
  Save, 
  HelpCircle,
  Building,
  DollarSign,
  UserCheck,
  Upload,
  FileJson,
  X,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';

// ─── JSON Key Mapping: flexible aliases → internal field names ──────────────
const COMPANY_KEY_MAP = {
  company_name:    ['company_name','companyName','name','corporate_name','corporateName','company'],
  industry:        ['industry','primary_industry','primaryIndustry','sector','industry_sector'],
  sub_industry:    ['sub_industry','subIndustry','sub_sector','subSector','category'],
  company_size:    ['company_size','companySize','size','employees','employee_count'],
  website:         ['website','url','company_url','companyUrl','web'],
  hq_country:      ['hq_country','hqCountry','country','headquarters','headquarters_country','headquartersCountry'],
  geo_market:      ['geo_market','geoMarket','geographic_markets','geographicMarkets','markets','regions'],
  founded_year:    ['founded_year','foundedYear','founded','year_founded','yearFounded'],
  business_model:  ['business_model','businessModel','model','biz_model'],
  target_customer: ['target_customer','targetCustomer','customer','target','customer_type'],
  description:     ['description','about','overview','company_description','companyDescription','summary'],
};

const KPI_KEY_MAP = {
  monthly_revenue:  ['monthly_revenue','monthlyRevenue','revenue','mrr'],
  revenue_target:   ['revenue_target','revenueTarget','rev_target','target_revenue','targetRevenue'],
  monthly_leads:    ['monthly_leads','monthlyLeads','leads','lead_volume','leadVolume'],
  lead_target:      ['lead_target','leadTarget','target_leads','targetLeads'],
  avg_deal_size:    ['avg_deal_size','avgDealSize','deal_size','dealSize','average_deal'],
  sales_cycle_days: ['sales_cycle_days','salesCycleDays','sales_cycle','salesCycle','cycle_days'],
  cac:              ['cac','customer_acquisition_cost','customerAcquisitionCost','acquisition_cost'],
  ltv:              ['ltv','lifetime_value','lifetimeValue','customer_ltv','customerLtv'],
  conversion_rate:  ['conversion_rate','conversionRate','conversion','cvr'],
  win_rate:         ['win_rate','winRate','win','close_rate','closeRate'],
  top_channel:      ['top_channel','topChannel','channel','best_channel','primary_channel'],
  currency:         ['currency','cur'],
  sales_team_size:  ['sales_team_size','salesTeamSize','team_size','teamSize','sales_reps'],
  active_campaigns: ['active_campaigns','activeCampaigns','campaigns'],
};

const ICP_KEY_MAP = {
  icp_industry:         ['icp_industry','icpIndustry','target_industry','targetIndustry','industry'],
  icp_company_size:     ['icp_company_size','icpCompanySize','target_size','targetSize','company_size'],
  icp_revenue_range:    ['icp_revenue_range','icpRevenueRange','revenue_range','revenueRange','target_revenue'],
  icp_job_titles:       ['icp_job_titles','icpJobTitles','job_titles','jobTitles','titles','roles'],
  icp_decision_makers:  ['icp_decision_makers','icpDecisionMakers','decision_makers','decisionMakers','personas'],
  icp_pain_points:      ['icp_pain_points','icpPainPoints','pain_points','painPoints','challenges'],
  icp_notes:            ['icp_notes','icpNotes','notes','additional_notes','additionalNotes'],
};

function resolveField(obj, aliases) {
  for (const key of aliases) {
    if (obj[key] !== undefined && obj[key] !== null && obj[key] !== '') {
      return obj[key];
    }
  }
  return undefined;
}

function parseJsonToCompany(obj) {
  const result = {};
  for (const [field, aliases] of Object.entries(COMPANY_KEY_MAP)) {
    const val = resolveField(obj, aliases);
    if (val !== undefined) result[field] = String(val);
  }
  return result;
}

function parseJsonToKpis(obj) {
  const result = {};
  for (const [field, aliases] of Object.entries(KPI_KEY_MAP)) {
    const val = resolveField(obj, aliases);
    if (val !== undefined) result[field] = val;
  }
  return result;
}

function parseJsonToIcp(obj) {
  const result = {};
  for (const [field, aliases] of Object.entries(ICP_KEY_MAP)) {
    const val = resolveField(obj, aliases);
    if (val !== undefined) {
      // Normalize arrays to comma-separated strings
      result[field] = Array.isArray(val) ? val.join(', ') : String(val);
    }
  }
  return result;
}

// ─── JSON Import Panel Component ────────────────────────────────────────────
function JsonImportPanel({ tab, onImport }) {
  const [dragging, setDragging] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [parseError, setParseError] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [fileName, setFileName] = useState('');
  const fileRef = useRef(null);

  const keyMapForTab = tab === 'company' ? COMPANY_KEY_MAP : tab === 'kpis' ? KPI_KEY_MAP : ICP_KEY_MAP;
  const parseForTab = tab === 'company' ? parseJsonToCompany : tab === 'kpis' ? parseJsonToKpis : parseJsonToIcp;

  const processFile = useCallback((file) => {
    if (!file) return;
    if (!file.name.endsWith('.json')) {
      setParseError('Only .json files are supported.');
      setParsed(null);
      return;
    }
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const raw = JSON.parse(e.target.result);
        // Support top-level or nested: { company: {...}, kpis: {...} }
        const section = raw[tab] || raw['company_profile'] || raw['kpi'] || raw['icp_profile'] || raw;
        const mapped = parseForTab(section);
        if (Object.keys(mapped).length === 0) {
          setParseError('No recognizable fields found. Check the JSON structure or use the example template.');
          setParsed(null);
        } else {
          setParsed(mapped);
          setParseError('');
        }
      } catch {
        setParseError('Invalid JSON format. Please check the file and try again.');
        setParsed(null);
      }
    };
    reader.readAsText(file);
  }, [tab, parseForTab]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    processFile(file);
  }, [processFile]);

  const handleDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);

  const handleFileChange = (e) => {
    processFile(e.target.files[0]);
    e.target.value = '';
  };

  const handleApply = () => {
    if (parsed) {
      onImport(parsed);
      setParsed(null);
      setFileName('');
      setShowPreview(false);
    }
  };

  const handleClear = () => {
    setParsed(null);
    setFileName('');
    setParseError('');
    setShowPreview(false);
  };

  // Generate example JSON for this tab
  const downloadExample = () => {
    const examples = {
      company: {
        company_name: 'Acme Technologies Inc.',
        industry: 'Software / SaaS',
        sub_industry: 'Enterprise DevOps',
        company_size: '50-250 employees',
        website: 'https://acmecorp.com',
        hq_country: 'United States',
        geo_market: 'North America, EMEA',
        founded_year: '2018',
        business_model: 'B2B',
        target_customer: 'Mid-market Engineering Teams',
        description: 'Acme delivers cloud-native CI/CD automation for mid-market teams.'
      },
      kpis: {
        monthly_revenue: 125000,
        revenue_target: 200000,
        monthly_leads: 320,
        lead_target: 500,
        avg_deal_size: 8500,
        sales_cycle_days: 42,
        cac: 1200,
        ltv: 24000,
        conversion_rate: 3.4,
        win_rate: 28,
        top_channel: 'LinkedIn',
        currency: 'USD',
        sales_team_size: 8,
        active_campaigns: 4
      },
      icp: {
        icp_industry: 'FinTech, Healthcare, Retail',
        icp_company_size: '200-2000 employees',
        icp_revenue_range: '$10M – $250M ARR',
        icp_job_titles: ['VP Engineering', 'CTO', 'Director of DevOps'],
        icp_decision_makers: ['CTO', 'VP Engineering', 'Security Director'],
        icp_pain_points: ['slow release cycles', 'fragmented CI/CD tooling', 'compliance gaps'],
        icp_notes: 'Focus on companies undergoing digital transformation with active cloud migration projects.'
      }
    };
    const blob = new Blob([JSON.stringify(examples[tab], null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `marketmind_${tab}_example.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const fieldCount = parsed ? Object.keys(parsed).length : 0;
  const totalFields = Object.keys(keyMapForTab).length;

  return (
    <div className="mb-6 rounded-2xl border border-indigo-500/15 bg-indigo-950/10 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-indigo-500/10">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-600/20 flex items-center justify-center">
            <FileJson className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <p className="text-xs font-bold text-white tracking-wide">JSON Import</p>
            <p className="text-[10px] text-gray-500">Auto-fill form fields from a JSON file</p>
          </div>
        </div>
        <button
          type="button"
          onClick={downloadExample}
          className="flex items-center space-x-1.5 text-[10px] font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 px-3 py-1.5 rounded-lg transition-all"
        >
          <Download className="w-3 h-3" />
          <span>Example JSON</span>
        </button>
      </div>

      <div className="p-4 space-y-3">
        {/* Drop Zone */}
        {!parsed && (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileRef.current?.click()}
            className={`relative flex flex-col items-center justify-center gap-2 h-28 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200
              ${dragging
                ? 'border-indigo-400 bg-indigo-600/15 scale-[1.01]'
                : 'border-white/10 hover:border-indigo-500/40 hover:bg-indigo-950/20 bg-white/2'
              }`}
          >
            <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={handleFileChange} />
            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${dragging ? 'bg-indigo-600/30' : 'bg-white/5'}`}>
              <Upload className={`w-5 h-5 transition-colors ${dragging ? 'text-indigo-300' : 'text-gray-400'}`} />
            </div>
            <div className="text-center">
              <p className="text-xs font-semibold text-gray-300">
                {dragging ? 'Drop to import' : 'Drag & drop or click to browse'}
              </p>
              <p className="text-[10px] text-gray-500 mt-0.5">Supports .json files · Flexible key names accepted</p>
            </div>
          </div>
        )}

        {/* Error */}
        {parseError && (
          <div className="flex items-start space-x-2 bg-rose-500/10 border border-rose-500/20 rounded-xl p-3">
            <X className="w-3.5 h-3.5 text-rose-400 mt-0.5 shrink-0" />
            <p className="text-[10px] text-rose-400 font-medium leading-relaxed">{parseError}</p>
          </div>
        )}

        {/* Parsed Preview */}
        {parsed && (
          <div className="space-y-3">
            {/* Summary bar */}
            <div className="flex items-center justify-between bg-emerald-500/8 border border-emerald-500/20 rounded-xl px-4 py-2.5">
              <div className="flex items-center space-x-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <div>
                  <p className="text-xs font-bold text-white">{fileName}</p>
                  <p className="text-[10px] text-emerald-400 font-medium">
                    {fieldCount} of {totalFields} fields recognized
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setShowPreview(!showPreview)}
                  className="flex items-center space-x-1 text-[10px] font-semibold text-gray-400 hover:text-white transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
                >
                  {showPreview ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  <span>{showPreview ? 'Hide' : 'Preview'}</span>
                </button>
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-1 text-gray-500 hover:text-red-400 transition-colors rounded-lg hover:bg-white/5"
                  title="Discard"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Field preview grid */}
            {showPreview && (
              <div className="grid grid-cols-2 gap-1.5 max-h-44 overflow-y-auto custom-scrollbar pr-1">
                {Object.entries(parsed).map(([key, val]) => (
                  <div key={key} className="bg-white/3 border border-white/5 rounded-lg px-3 py-2">
                    <p className="text-[9px] font-bold text-gray-500 uppercase tracking-wider truncate">{key.replace(/_/g, ' ')}</p>
                    <p className="text-[10px] text-gray-200 font-medium mt-0.5 truncate" title={String(val)}>{String(val)}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Apply button */}
            <button
              type="button"
              onClick={handleApply}
              className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-600/20 active:scale-[0.98]"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Apply {fieldCount} Fields to Form</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Profile Page ───────────────────────────────────────────────────────
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
  const [icpJobTitles, setIcpJobTitles] = useState('');
  const [icpDecisionMakers, setIcpDecisionMakers] = useState('');
  const [icpPainPoints, setIcpPainPoints] = useState('');
  const [icpNotes, setIcpNotes] = useState('');

  const fetchProfileData = async () => {
    try {
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

      const icpRes = await fetch('/api/icp');
      if (icpRes.ok) {
        const icpData = await icpRes.json();
        const icp = icpData.profile || {};
        setIcpIndustry(icp.icp_industry || '');
        setIcpCompanySize(icp.icp_company_size || '');
        setIcpRevenueRange(icp.icp_revenue_range || '');
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

  useEffect(() => { fetchProfileData(); }, []);

  // ── JSON import handlers (per tab) ──────────────────────────────────────
  const handleJsonImport = useCallback((tab, mapped) => {
    if (tab === 'company') {
      if (mapped.company_name !== undefined)  setCompanyName(mapped.company_name);
      if (mapped.industry !== undefined)      setIndustry(mapped.industry);
      if (mapped.sub_industry !== undefined)  setSubIndustry(mapped.sub_industry);
      if (mapped.website !== undefined)       setWebsite(mapped.website);
      if (mapped.hq_country !== undefined)    setHqCountry(mapped.hq_country);
      if (mapped.geo_market !== undefined)    setGeoMarket(mapped.geo_market);
      if (mapped.founded_year !== undefined)  setFoundedYear(mapped.founded_year);
      if (mapped.business_model !== undefined) setBusinessModel(mapped.business_model);
      if (mapped.target_customer !== undefined) setTargetCustomer(mapped.target_customer);
      if (mapped.description !== undefined)   setDescription(mapped.description);
      // company_size: try to match existing dropdown options or fallback
      if (mapped.company_size !== undefined) {
        const sizeOptions = ['1-10 employees','10-50 employees','50-250 employees','250-1000 employees','1000+ employees'];
        const match = sizeOptions.find(o => o.toLowerCase().includes(mapped.company_size.toLowerCase().replace(/\s+/g, '')));
        setCompanySize(match || mapped.company_size);
      }
    } else if (tab === 'kpis') {
      if (mapped.monthly_revenue !== undefined)  setMonthlyRevenue(Number(mapped.monthly_revenue) || 0);
      if (mapped.revenue_target !== undefined)   setRevenueTarget(Number(mapped.revenue_target) || 0);
      if (mapped.monthly_leads !== undefined)    setMonthlyLeads(Number(mapped.monthly_leads) || 0);
      if (mapped.lead_target !== undefined)      setLeadTarget(Number(mapped.lead_target) || 0);
      if (mapped.avg_deal_size !== undefined)    setAvgDealSize(Number(mapped.avg_deal_size) || 0);
      if (mapped.sales_cycle_days !== undefined) setSalesCycleDays(Number(mapped.sales_cycle_days) || 0);
      if (mapped.cac !== undefined)              setCac(Number(mapped.cac) || 0);
      if (mapped.ltv !== undefined)              setLtv(Number(mapped.ltv) || 0);
      if (mapped.conversion_rate !== undefined)  setConversionRate(Number(mapped.conversion_rate) || 0);
      if (mapped.win_rate !== undefined)         setWinRate(Number(mapped.win_rate) || 0);
      if (mapped.top_channel !== undefined)      setTopChannel(String(mapped.top_channel));
      if (mapped.currency !== undefined)         setCurrency(String(mapped.currency));
      if (mapped.sales_team_size !== undefined)  setSalesTeamSize(Number(mapped.sales_team_size) || 0);
      if (mapped.active_campaigns !== undefined) setActiveCampaigns(Number(mapped.active_campaigns) || 0);
    } else if (tab === 'icp') {
      if (mapped.icp_industry !== undefined)        setIcpIndustry(mapped.icp_industry);
      if (mapped.icp_company_size !== undefined)    setIcpCompanySize(mapped.icp_company_size);
      if (mapped.icp_revenue_range !== undefined)   setIcpRevenueRange(mapped.icp_revenue_range);
      if (mapped.icp_job_titles !== undefined)      setIcpJobTitles(mapped.icp_job_titles);
      if (mapped.icp_decision_makers !== undefined) setIcpDecisionMakers(mapped.icp_decision_makers);
      if (mapped.icp_pain_points !== undefined)     setIcpPainPoints(mapped.icp_pain_points);
      if (mapped.icp_notes !== undefined)           setIcpNotes(mapped.icp_notes);
    }
    setSuccess(`✓ ${Object.keys(mapped).length} fields imported from JSON. Review and save to persist.`);
    setTimeout(() => setSuccess(''), 5000);
  }, []);

  // ── Save handlers ────────────────────────────────────────────────────────
  const handleSaveCompany = async (e) => {
    e.preventDefault();
    setSaving(true); setSuccess(''); setError('');
    try {
      const res = await fetch('/api/onboarding/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
        body: JSON.stringify({ business: { company_name: companyName, industry, sub_industry: subIndustry, size: companySize, website, description, hq_country: hqCountry, geo_market: geoMarket, business_model: businessModel, target_customer: targetCustomer, founded_year: foundedYear } })
      });
      if (res.ok) setSuccess('Company profile parameters saved successfully!');
      else setError('Failed to save profile details.');
    } catch (err) { setError('Communication error.'); }
    finally { setSaving(false); }
  };

  const handleSaveKPIs = async (e) => {
    e.preventDefault();
    setSaving(true); setSuccess(''); setError('');
    try {
      const res = await fetch('/api/company-metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
        body: JSON.stringify({ monthly_revenue: monthlyRevenue, revenue_target: revenueTarget, monthly_leads: monthlyLeads, lead_target: leadTarget, active_campaigns: activeCampaigns, conversion_rate: conversionRate, avg_deal_size: avgDealSize, sales_cycle_days: salesCycleDays, top_channel: topChannel, currency, sales_team_size: salesTeamSize, win_rate: winRate, cac, ltv })
      });
      if (res.ok) setSuccess('Company business health KPIs updated successfully!');
      else setError('Failed to update KPIs.');
    } catch (err) { setError('Network communication failed.'); }
    finally { setSaving(false); }
  };

  const handleSaveICP = async (e) => {
    e.preventDefault();
    setSaving(true); setSuccess(''); setError('');
    const jobTitlesArr = icpJobTitles.split(',').map(s => s.trim()).filter(Boolean);
    const decisionMakersArr = icpDecisionMakers.split(',').map(s => s.trim()).filter(Boolean);
    const painPointsArr = icpPainPoints.split(',').map(s => s.trim()).filter(Boolean);
    try {
      const res = await fetch('/api/icp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
        body: JSON.stringify({ icp_industry: icpIndustry, icp_company_size: icpCompanySize, icp_revenue_range: icpRevenueRange, icp_job_titles: jobTitlesArr, icp_decision_makers: decisionMakersArr, icp_pain_points: painPointsArr, icp_notes: icpNotes })
      });
      if (res.ok) setSuccess('Ideal Customer Profile (ICP) parameters stored successfully!');
      else setError('Failed to update ICP profile.');
    } catch (err) { setError('Network communication failure.'); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">Settings &amp; KPIs</h1>
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
                onClick={() => { setActiveTab(tab.id); setSuccess(''); setError(''); }}
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
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-sm text-emerald-400 font-medium max-w-4xl flex items-start space-x-2">
          <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{success}</span>
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

          {/* ── TAB 1: COMPANY PROFILE ── */}
          {activeTab === 'company' && (
            <div className="space-y-0">
              <JsonImportPanel tab="company" onImport={(mapped) => handleJsonImport('company', mapped)} />
              <GlassCard className="border border-white/5">
                <form onSubmit={handleSaveCompany} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Name</label>
                      <input type="text" required value={companyName} onChange={(e) => setCompanyName(e.target.value)} className="w-full glass-input" placeholder="e.g. Acme Corp" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Primary Industry Sector</label>
                      <input type="text" required value={industry} onChange={(e) => setIndustry(e.target.value)} className="w-full glass-input" placeholder="e.g. Technology, Supply Chain" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Sub-Industry / Category</label>
                      <input type="text" value={subIndustry} onChange={(e) => setSubIndustry(e.target.value)} className="w-full glass-input" placeholder="e.g. Identity Access Management" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Company Size</label>
                      <select value={companySize} onChange={(e) => setCompanySize(e.target.value)} className="w-full glass-input">
                        <option value="1-10 employees">1 – 10 employees</option>
                        <option value="10-50 employees">10 – 50 employees</option>
                        <option value="50-250 employees">50 – 250 employees</option>
                        <option value="250-1000 employees">250 – 1000 employees</option>
                        <option value="1000+ employees">1,000+ employees</option>
                      </select>
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Website</label>
                      <input type="url" value={website} onChange={(e) => setWebsite(e.target.value)} className="w-full glass-input" placeholder="https://company.com" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Headquarters Country</label>
                      <input type="text" value={hqCountry} onChange={(e) => setHqCountry(e.target.value)} className="w-full glass-input" placeholder="e.g. United States" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Geographic Target Markets</label>
                      <input type="text" value={geoMarket} onChange={(e) => setGeoMarket(e.target.value)} className="w-full glass-input" placeholder="e.g. North America, APAC" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Founded Year</label>
                      <input type="text" value={foundedYear} onChange={(e) => setFoundedYear(e.target.value)} className="w-full glass-input" placeholder="e.g. 2021" />
                    </div>
                  </div>
                  <div className="text-xs">
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Corporate Business Model</label>
                    <select value={businessModel} onChange={(e) => setBusinessModel(e.target.value)} className="w-full glass-input">
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
                    <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows="3" className="w-full glass-input" placeholder="Describe your core product offerings, target buyers, and key differentiation points..."></textarea>
                  </div>
                  <button type="submit" disabled={saving} className="glass-button-primary flex items-center justify-center space-x-2 px-5 py-2.5 text-xs font-semibold disabled:opacity-40">
                    <Save className="w-4 h-4" /><span>Save Profile Parameters</span>
                  </button>
                </form>
              </GlassCard>
            </div>
          )}

          {/* ── TAB 2: KPIs ── */}
          {activeTab === 'kpis' && (
            <div className="space-y-0">
              <JsonImportPanel tab="kpis" onImport={(mapped) => handleJsonImport('kpis', mapped)} />
              <GlassCard className="border border-white/5">
                <form onSubmit={handleSaveKPIs} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Revenue (Base)</label>
                      <input type="number" value={monthlyRevenue} onChange={(e) => setMonthlyRevenue(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Revenue Target</label>
                      <input type="number" value={revenueTarget} onChange={(e) => setRevenueTarget(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Leads volume</label>
                      <input type="number" value={monthlyLeads} onChange={(e) => setMonthlyLeads(parseInt(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Monthly Leads Target</label>
                      <input type="number" value={leadTarget} onChange={(e) => setLeadTarget(parseInt(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Sales Cycle Duration (Days)</label>
                      <input type="number" value={salesCycleDays} onChange={(e) => setSalesCycleDays(parseInt(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Average Deal Size (USD)</label>
                      <input type="number" value={avgDealSize} onChange={(e) => setAvgDealSize(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Acquisition Cost (CAC)</label>
                      <input type="number" value={cac} onChange={(e) => setCac(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Customer Lifetime Value (LTV)</label>
                      <input type="number" value={ltv} onChange={(e) => setLtv(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Lead Conversion Rate (%)</label>
                      <input type="number" step="0.01" value={conversionRate} onChange={(e) => setConversionRate(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Sales Win Rate (%)</label>
                      <input type="number" step="0.01" value={winRate} onChange={(e) => setWinRate(parseFloat(e.target.value))} className="w-full glass-input" />
                    </div>
                  </div>
                  <button type="submit" disabled={saving} className="glass-button-primary flex items-center justify-center space-x-2 px-5 py-2.5 text-xs font-semibold disabled:opacity-40">
                    <Save className="w-4 h-4" /><span>Update Dashboard KPIs</span>
                  </button>
                </form>
              </GlassCard>
            </div>
          )}

          {/* ── TAB 3: ICP ── */}
          {activeTab === 'icp' && (
            <div className="space-y-0">
              <JsonImportPanel tab="icp" onImport={(mapped) => handleJsonImport('icp', mapped)} />
              <GlassCard className="border border-white/5">
                <form onSubmit={handleSaveICP} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Industry Sector</label>
                      <input type="text" value={icpIndustry} onChange={(e) => setIcpIndustry(e.target.value)} placeholder="e.g. Retail, FinTech" className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Company Size</label>
                      <input type="text" value={icpCompanySize} onChange={(e) => setIcpCompanySize(e.target.value)} placeholder="e.g. 500-1000 employees" className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Revenue Range</label>
                      <input type="text" value={icpRevenueRange} onChange={(e) => setIcpRevenueRange(e.target.value)} placeholder="e.g. $20M – $100M ARR" className="w-full glass-input" />
                    </div>
                    <div>
                      <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Job Titles (Comma-separated)</label>
                      <input type="text" value={icpJobTitles} onChange={(e) => setIcpJobTitles(e.target.value)} placeholder="e.g. VP Operations, Chief Information Officer" className="w-full glass-input" />
                    </div>
                  </div>
                  <div className="text-xs">
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Ideal Decision Maker Personas (Comma-separated)</label>
                    <input type="text" value={icpDecisionMakers} onChange={(e) => setIcpDecisionMakers(e.target.value)} placeholder="e.g. VP Engineering, Security Director" className="w-full glass-input" />
                  </div>
                  <div className="text-xs">
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">Target ICP Pain Points (Comma-separated)</label>
                    <textarea value={icpPainPoints} onChange={(e) => setIcpPainPoints(e.target.value)} rows="2" className="w-full glass-input" placeholder="e.g. high SaaS stack overhead, slow developer onboarding"></textarea>
                  </div>
                  <div className="text-xs">
                    <label className="block font-semibold text-gray-400 uppercase tracking-wider mb-2">ICP Account Notes</label>
                    <textarea value={icpNotes} onChange={(e) => setIcpNotes(e.target.value)} rows="3" className="w-full glass-input" placeholder="Enter additional parameters or grounding guidance for target account profiling..."></textarea>
                  </div>
                  <button type="submit" disabled={saving} className="glass-button-primary flex items-center justify-center space-x-2 px-5 py-2.5 text-xs font-semibold disabled:opacity-40">
                    <Save className="w-4 h-4" /><span>Update Buyer ICP Details</span>
                  </button>
                </form>
              </GlassCard>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
