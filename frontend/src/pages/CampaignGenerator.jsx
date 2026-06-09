import React, { useState } from 'react';
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
  const [product, setProduct] = useState('Eco-Friendly Smart Packaging');
  const [audience, setAudience] = useState('E-commerce brands and cosmetics retailers looking to improve sustainability');
  const [platform, setPlatform] = useState('Instagram & Google Search');
  const [goals, setGoals] = useState('Customer acquisition and sustainability branding');
  const [budget, setBudget] = useState('$8,000 - $20,000');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState('');

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
          <div className="flex items-center space-x-2 border-b border-white/5 pb-3 mb-6">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Campaign configuration</h2>
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
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Primary Ad Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full glass-input"
              >
                <option value="LinkedIn">LinkedIn Sponsored Content</option>
                <option value="Instagram">Instagram Stories & Feed</option>
                <option value="Google Search">Google Search Ads</option>
                <option value="Multi-platform">Multi-platform Mix</option>
              </select>
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
              <div className="flex border-b border-white/5 text-sm">
                {[
                  { id: 'overview', label: 'Overview', icon: FileText },
                  { id: 'audience', label: 'Persona Profile', icon: Eye },
                  { id: 'funnel', label: 'Funnel tactics', icon: Layers },
                  { id: 'content', label: 'Ads & Copy', icon: Send },
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
                        {(result.strategic_goals || []).length > 0 ? (
                          result.strategic_goals.map((goal, idx) => (
                            <div key={idx} className="bg-white/2 p-4 rounded-xl border border-white/5 space-y-2">
                              <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                                <span className="w-5 h-5 rounded-full bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-xs font-bold">{idx+1}</span>
                                <span>{goal.goal_name || goal}</span>
                              </h4>
                              {goal.business_context && <p className="text-xs text-gray-400">{goal.business_context}</p>}
                            </div>
                          ))
                        ) : (
                          (result.objectives || []).map((obj, idx) => (
                            <div key={idx} className="bg-white/2 p-4 rounded-xl border border-white/5 flex items-center space-x-3 text-sm text-gray-300">
                              <CheckCircle className="w-5 h-5 text-indigo-400 shrink-0" />
                              <span>{obj}</span>
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
                              <span>{pt}</span>
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
                              <span>{gl}</span>
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
                                  <span key={i} className="bg-white/5 px-2 py-1 rounded text-white font-medium">{tac}</span>
                                ))}
                              </div>
                            </div>
                            <div>
                              <h5 className="font-bold text-gray-400 uppercase tracking-wider mb-2">Metrics monitored</h5>
                              <ul className="space-y-1 text-gray-300">
                                {(stageData.kpis || []).map((kp, i) => (
                                  <li key={i} className="flex items-center space-x-1.5">
                                    <span className="w-1 h-1 rounded-full bg-white/20"></span>
                                    <span>{kp}</span>
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
    </div>
  );
}
