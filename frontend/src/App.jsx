import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import Auth from './components/Auth.jsx';
import Dashboard from './pages/Dashboard.jsx';
import CampaignGenerator from './pages/CampaignGenerator.jsx';
import SalesPitchCreator from './pages/SalesPitchCreator.jsx';
import LeadScoring from './pages/LeadScoring.jsx';
import MarketAnalysis from './pages/MarketAnalysis.jsx';
import BusinessInsights from './pages/BusinessInsights.jsx';
import CRM from './pages/CRM.jsx';
import KnowledgeBase from './pages/KnowledgeBase.jsx';
import Profile from './pages/Profile.jsx';
import LogoMaker from './pages/LogoMaker.jsx';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [csrfToken, setCsrfToken] = useState('');

  // Fetch CSRF token and check current logged-in user on mount
  useEffect(() => {
    async function checkAuth() {
      try {
        // Fetch session info
        const res = await fetch('/api/auth/me');
        if (res.ok) {
          const data = await res.json();
          setUser(data.user);
        } else {
          setUser(null);
        }
      } catch (err) {
        console.error("Auth check failed:", err);
      } finally {
        setLoading(false);
      }
    }
    checkAuth();
  }, []);

  // Helper to extract CSRF token from cookie
  const getCsrfToken = () => {
    const name = 'csrf_token=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';');
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i].trim();
      if (c.indexOf(name) === 0) {
        return c.substring(name.length, c.length);
      }
    }
    return '';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-theme-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400 font-display font-medium">Initializing MarketMind AI...</p>
        </div>
      </div>
    );
  }

  // If user is not logged in, display the login/register screen
  if (!user) {
    return <Auth onAuthSuccess={(userData) => setUser(userData)} />;
  }

  return (
    <Router>
      <Layout user={user} onLogout={() => setUser(null)}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard getCsrfToken={getCsrfToken} />} />
          <Route path="/campaigns" element={<CampaignGenerator getCsrfToken={getCsrfToken} />} />
          <Route path="/pitch" element={<SalesPitchCreator getCsrfToken={getCsrfToken} />} />
          <Route path="/logo-maker" element={<LogoMaker getCsrfToken={getCsrfToken} />} />
          <Route path="/leads" element={<LeadScoring getCsrfToken={getCsrfToken} />} />
          <Route path="/market" element={<MarketAnalysis getCsrfToken={getCsrfToken} />} />
          <Route path="/insights" element={<BusinessInsights getCsrfToken={getCsrfToken} />} />
          <Route path="/crm" element={<CRM getCsrfToken={getCsrfToken} />} />
          <Route path="/knowledge" element={<KnowledgeBase getCsrfToken={getCsrfToken} />} />
          <Route path="/profile" element={<Profile user={user} setUser={setUser} getCsrfToken={getCsrfToken} />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}
