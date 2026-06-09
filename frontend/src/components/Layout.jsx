import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Send, 
  FileText, 
  UserCheck, 
  TrendingUp, 
  Lightbulb, 
  Briefcase, 
  Layers, 
  Database, 
  Settings, 
  LogOut, 
  Bell, 
  ChevronDown, 
  Globe, 
  Flame,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

export default function Layout({ children, user, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [stockPrices, setStockPrices] = useState([]);
  const [activities, setActivities] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [companyName, setCompanyName] = useState('MarketMind AI');

  // Navigation Items
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Campaign Generator', path: '/campaigns', icon: Send },
    { name: 'Sales Pitch Creator', path: '/pitch', icon: FileText },
    { name: 'Lead Scoring', path: '/leads', icon: UserCheck },
    { name: 'Market Analysis', path: '/market', icon: TrendingUp },
    { name: 'Business Insights', path: '/insights', icon: Lightbulb },
    { name: 'CRM Pipeline', path: '/crm', icon: Briefcase },
    { name: 'Enterprise Analyzer', path: '/workspace', icon: Layers },
    { name: 'Knowledge Base', path: '/knowledge', icon: Database },
    { name: 'Profile & KPIs', path: '/profile', icon: Settings },
  ];

  // Fetch stocks & activity logs periodically
  useEffect(() => {
    async function fetchData() {
      try {
        const statsRes = await fetch('/api/dashboard/stats');
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          if (statsData.stats?.stocks) {
            setStockPrices(statsData.stats.stocks);
          }
          if (statsData.company_metrics?.company_name) {
            setCompanyName(statsData.company_metrics.company_name);
          }
        }
        
        const activityRes = await fetch('/api/activity?limit=5');
        if (activityRes.ok) {
          const actData = await activityRes.json();
          setActivities(actData.activities || []);
        }
      } catch (err) {
        console.error("Layout data fetch error:", err);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const handleLogoutClick = async () => {
    try {
      const res = await fetch('/api/auth/logout', { method: 'POST' });
      if (res.ok) {
        onLogout();
        navigate('/');
      }
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  return (
    <div className="flex min-h-screen bg-surface-900 text-gray-200 overflow-hidden font-sans relative">
      {/* Decorative ambient mesh gradients */}
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none animate-float"></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-cyan-500/5 blur-[120px] pointer-events-none animate-float-delayed"></div>

      {/* Sidebar */}
      <aside className="w-64 bg-surface-800/80 border-r border-white/5 flex flex-col z-20 backdrop-blur-xl">
        {/* Logo Section */}
        <div className="p-6 flex items-center space-x-3 border-b border-white/5">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <Flame className="w-6 h-6 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-display font-bold text-white tracking-wide leading-none">MarketMind</h1>
            <span className="text-xs text-indigo-400 font-medium tracking-widest uppercase">Intelligence</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 font-medium text-sm group
                  ${isActive 
                    ? 'bg-indigo-600/20 text-white border-l-4 border-indigo-500 shadow-inner' 
                    : 'text-gray-400 hover:text-white hover:bg-white/5'}
                `}
              >
                <Icon className={`w-5 h-5 transition-transform duration-300 group-hover:scale-110 ${isActive ? 'text-indigo-400' : 'text-gray-400 group-hover:text-white'}`} />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sidebar Footer User Info */}
        <div className="p-4 border-t border-white/5 bg-surface-900/40 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-indigo-600/30 border border-indigo-500/20 flex items-center justify-center font-display font-semibold text-indigo-400">
              {user.avatar || user.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="truncate w-32">
              <p className="text-sm font-medium text-white truncate leading-tight">{user.name}</p>
              <p className="text-xs text-gray-500 truncate leading-none mt-1">{user.email}</p>
            </div>
          </div>
          <button 
            onClick={handleLogoutClick}
            title="Log Out"
            className="p-2 text-gray-500 hover:text-red-400 hover:bg-white/5 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Header */}
        <header className="h-16 bg-surface-800/40 border-b border-white/5 flex items-center justify-between px-8 z-10 backdrop-blur-xl">
          {/* Workspace Title & Stock Ticker */}
          <div className="flex items-center space-x-6 overflow-hidden flex-1 max-w-2xl mr-4">
            <div className="flex items-center space-x-2 text-sm text-gray-400 border-r border-white/10 pr-6 shrink-0">
              <Globe className="w-4 h-4 text-indigo-400" />
              <span className="font-semibold text-white truncate max-w-36">{companyName}</span>
            </div>

            {/* Live Ticker */}
            <div className="flex items-center space-x-6 overflow-x-auto no-scrollbar py-1 text-xs shrink-0 select-none custom-scrollbar">
              {stockPrices.map((stock) => {
                const isPositive = stock.change_pct >= 0;
                return (
                  <div key={stock.ticker} className="flex items-center space-x-2 bg-white/5 px-2.5 py-1 rounded-md border border-white/5">
                    <span className="font-bold text-gray-300">{stock.ticker}</span>
                    <span className="text-white font-medium">{stock.price.toFixed(2)}</span>
                    <span className={`flex items-center font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isPositive ? <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" /> : <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />}
                      {Math.abs(stock.change_pct).toFixed(2)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Header Operations */}
          <div className="flex items-center space-x-4 shrink-0 relative">
            {/* Notification Bell */}
            <div className="relative">
              <button 
                onClick={() => {
                  setShowNotifications(!showNotifications);
                  setShowProfileMenu(false);
                }}
                className={`p-2 rounded-xl transition-all relative hover:bg-white/5 ${showNotifications ? 'bg-indigo-600/10 text-indigo-400' : 'text-gray-400 hover:text-white'}`}
              >
                <Bell className="w-5 h-5" />
                {activities.length > 0 && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full animate-ping"></span>
                )}
              </button>

              {/* Notification Dropdown */}
              {showNotifications && (
                <div className="absolute right-0 mt-3 w-80 glass-panel rounded-2xl p-4 shadow-xl z-30">
                  <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                    <h3 className="text-sm font-semibold text-white">Recent Activity Log</h3>
                    <span className="text-xs text-indigo-400 font-medium">Auto-updated</span>
                  </div>
                  <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar pr-1">
                    {activities.length === 0 ? (
                      <p className="text-xs text-gray-500 text-center py-4">No recent activity detected.</p>
                    ) : (
                      activities.map((act) => (
                        <div key={act.id} className="text-xs border-b border-white/5 pb-2 last:border-0 last:pb-0">
                          <p className="text-white font-medium">{act.title}</p>
                          <div className="flex items-center justify-between text-[10px] text-gray-500 mt-1">
                            <span className="bg-white/5 px-1.5 py-0.5 rounded text-indigo-400 uppercase tracking-wider font-semibold">{act.activity_type}</span>
                            <span>{new Date(act.created_at).toLocaleTimeString()}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Profile Dropdown */}
            <div className="relative">
              <button 
                onClick={() => {
                  setShowProfileMenu(!showProfileMenu);
                  setShowNotifications(false);
                }}
                className="flex items-center space-x-2 p-1.5 rounded-xl hover:bg-white/5 transition-all text-gray-400 hover:text-white"
              >
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 flex items-center justify-center font-display font-semibold text-indigo-400">
                  {user.avatar || user.name?.[0]?.toUpperCase()}
                </div>
                <ChevronDown className="w-4 h-4" />
              </button>

              {showProfileMenu && (
                <div className="absolute right-0 mt-3 w-48 glass-panel rounded-xl py-2 shadow-xl z-30">
                  <button 
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate('/profile');
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors"
                  >
                    Settings & Profile
                  </button>
                  <button 
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate('/crm');
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors"
                  >
                    CRM Leads
                  </button>
                  <div className="border-t border-white/5 my-1"></div>
                  <button 
                    onClick={() => {
                      setShowProfileMenu(false);
                      handleLogoutClick();
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/5 hover:text-red-300 transition-colors flex items-center space-x-2"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* View Port */}
        <main className="flex-1 overflow-y-auto p-8 custom-scrollbar relative z-0">
          {children}
        </main>
      </div>
    </div>
  );
}
