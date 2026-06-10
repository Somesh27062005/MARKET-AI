import React, { useState } from 'react';
import { Flame, Mail, Lock, User, RefreshCw, LogIn, Globe } from 'lucide-react';
import GlassCard from './GlassCard.jsx';

export default function Auth({ onAuthSuccess }) {
  const [view, setView] = useState('login'); // 'login' | 'register' | 'reset'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    let endpoint = '/api/auth/login';
    let payload = { email, password };

    if (view === 'register') {
      endpoint = '/api/auth/register';
      payload = { email, password, name };
    } else if (view === 'reset') {
      endpoint = '/api/auth/reset-password';
      payload = { email, newPassword: password };
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        if (view === 'login') {
          onAuthSuccess(data.user);
        } else if (view === 'register') {
          setSuccess('Account created successfully! Logging in...');
          setTimeout(() => {
            onAuthSuccess(data.user);
          }, 1000);
        } else {
          setSuccess('Password updated successfully! You can now log in.');
          setView('login');
        }
      } else {
        setError(data.error || 'Authentication failed. Please try again.');
      }
    } catch (err) {
      console.error(err);
      setError('A network error occurred. Is the Flask backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // Redirect browser directly to the Flask OAuth endpoint
    window.location.href = '/api/auth/google';
  };

  return (
    <div className="min-h-screen bg-surface-900 flex items-center justify-center p-4 relative font-sans">
      {/* Background abstract glowing circles */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl -z-10"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl -z-10"></div>

      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-xl shadow-indigo-600/25 mb-3">
            <Flame className="w-8 h-8 text-white animate-pulse" />
          </div>
          <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">MarketMind AI</h1>
          <p className="text-sm text-indigo-400 font-medium tracking-wide uppercase mt-1">Intelligence Platform</p>
        </div>

        {/* Auth Box */}
        <GlassCard className="border border-white/10 shadow-2xl relative">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-display font-bold text-white uppercase tracking-wide">
              {view === 'login' && 'Sign In'}
              {view === 'register' && 'Create Account'}
              {view === 'reset' && 'Reset Password'}
            </h2>
            <span className="text-xs text-gray-500 font-medium bg-white/5 py-1 px-2.5 rounded-lg border border-white/5">
              Secure Auth
            </span>
          </div>

          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 mb-4 text-xs text-rose-400 font-medium animate-shake">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 mb-4 text-xs text-emerald-400 font-medium">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {view === 'register' && (
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full pl-10 pr-4 glass-input bg-surface-900/60"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-10 pr-4 glass-input bg-surface-900/60"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  {view === 'reset' ? 'New Password' : 'Password'}
                </label>
                {view === 'login' && (
                  <button 
                    type="button"
                    onClick={() => {
                      setView('reset');
                      setPassword('');
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                  >
                    Forgot?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 glass-input bg-surface-900/60"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full glass-button-primary mt-6 flex items-center justify-center space-x-2 py-2.5 disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>
                    {view === 'login' && 'Sign In'}
                    {view === 'register' && 'Sign Up'}
                    {view === 'reset' && 'Reset Password'}
                  </span>
                </>
              )}
            </button>
          </form>

          {/* Social Sign-in Divider */}
          <div className="flex items-center my-6">
            <div className="flex-1 border-t border-white/5"></div>
            <span className="text-xs text-gray-500 px-3 uppercase tracking-wider">Or Continue With</span>
            <div className="flex-1 border-t border-white/5"></div>
          </div>

          <button
            onClick={handleGoogleLogin}
            className="w-full glass-button-secondary flex items-center justify-center space-x-2 py-2 text-sm bg-white/5 hover:bg-white/10"
          >
            <Globe className="w-4 h-4 text-rose-500" />
            <span>Google Workspace</span>
          </button>

          {/* Bottom Switch Links */}
          <div className="mt-6 text-center text-xs text-gray-500 font-medium">
            {view === 'login' && (
              <p>
                Don't have an account?{' '}
                <button 
                  onClick={() => {
                    setView('register');
                    setName('');
                    setError('');
                  }}
                  className="text-indigo-400 hover:text-indigo-300 font-semibold"
                >
                  Create free account
                </button>
              </p>
            )}

            {view !== 'login' && (
              <p>
                Already have an account?{' '}
                <button 
                  onClick={() => {
                    setView('login');
                    setError('');
                  }}
                  className="text-indigo-400 hover:text-indigo-300 font-semibold"
                >
                  Sign in here
                </button>
              </p>
            )}
          </div>
        </GlassCard>

        {/* Demo credentials hint (removed) */}
      </div>
    </div>
  );
}
