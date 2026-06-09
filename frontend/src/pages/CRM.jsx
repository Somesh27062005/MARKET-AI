import React, { useState, useEffect } from 'react';
import { 
  Briefcase, 
  Trash2, 
  ChevronLeft, 
  ChevronRight, 
  UserCheck, 
  Plus,
  HelpCircle,
  TrendingUp,
  X,
  Edit3
} from 'lucide-react';
import GlassCard from '../components/GlassCard.jsx';

const COLUMNS = ['New', 'Contacted', 'Proposal', 'Closed Won'];
const COLUMN_COLORS = {
  'New': 'border-indigo-500 bg-indigo-500/10 text-indigo-400',
  'Contacted': 'border-cyan-500 bg-cyan-500/10 text-cyan-400',
  'Proposal': 'border-amber-500 bg-amber-500/10 text-amber-400',
  'Closed Won': 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
};

export default function CRM({ getCsrfToken }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(null); // stores lead being edited
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [score, setScore] = useState(70);
  const [grade, setGrade] = useState('B');
  const [details, setDetails] = useState('');

  // Fetch leads on mount
  const fetchLeads = async () => {
    try {
      const res = await fetch('/api/crm/leads');
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads || []);
      }
    } catch (err) {
      console.error("CRM leads fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleCreateLead = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/crm/leads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ name, company, score, grade, details })
      });

      if (res.ok) {
        setShowAddModal(false);
        setName('');
        setCompany('');
        setDetails('');
        fetchLeads();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateStatus = async (lead, newStatus) => {
    try {
      const res = await fetch(`/api/crm/leads/${lead.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ status: newStatus })
      });

      if (res.ok) {
        fetchLeads();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleEditLead = async (e) => {
    e.preventDefault();
    if (!showEditModal) return;
    try {
      const res = await fetch(`/api/crm/leads/${showEditModal.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ name, company, score, grade, details })
      });

      if (res.ok) {
        setShowEditModal(null);
        setName('');
        setCompany('');
        setDetails('');
        fetchLeads();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteLead = async (leadId) => {
    if (!confirm('Are you sure you want to remove this lead?')) return;
    try {
      const res = await fetch(`/api/crm/leads/${leadId}`, {
        method: 'DELETE',
        headers: {
          'X-CSRF-Token': getCsrfToken()
        }
      });

      if (res.ok) {
        fetchLeads();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const moveLead = (lead, direction) => {
    const currentIndex = COLUMNS.indexOf(lead.status);
    const nextIndex = currentIndex + direction;
    if (nextIndex >= 0 && nextIndex < COLUMNS.length) {
      handleUpdateStatus(lead, COLUMNS[nextIndex]);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-white tracking-wide">CRM Sales Pipeline</h1>
          <p className="text-gray-400 mt-1">Manage qualified sales opportunities and monitor deal progression stages.</p>
        </div>
        <button 
          onClick={() => {
            setName('');
            setCompany('');
            setScore(70);
            setGrade('B');
            setDetails('');
            setShowAddModal(true);
          }}
          className="glass-button-primary flex items-center space-x-2 text-xs font-semibold py-2 px-3"
        >
          <Plus className="w-4 h-4" />
          <span>Add Lead Manually</span>
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : leads.length === 0 ? (
        <GlassCard className="flex-1 flex flex-col items-center justify-center text-center space-y-4 border border-white/5">
          <Briefcase className="w-12 h-12 text-gray-600" />
          <div>
            <h3 className="text-lg font-semibold text-white">Sales pipeline is empty</h3>
            <p className="text-xs text-gray-500 mt-1">
              Add leads manually or export qualified prospect scores from the <strong>Lead Scoring</strong> workflow.
            </p>
          </div>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 items-start flex-1 overflow-x-auto custom-scrollbar pb-4">
          {COLUMNS.map((column) => {
            const columnLeads = leads.filter(l => l.status === column);
            return (
              <div key={column} className="flex flex-col space-y-4 min-w-[260px]">
                {/* Column Title */}
                <div className={`border-l-4 px-3 py-1.5 rounded-r-lg font-display font-bold text-xs uppercase tracking-wider flex justify-between items-center ${COLUMN_COLORS[column]}`}>
                  <span>{column}</span>
                  <span className="bg-white/5 py-0.5 px-2 rounded-full font-mono text-[10px]">{columnLeads.length}</span>
                </div>

                {/* Column Cards */}
                <div className="space-y-3 min-h-[300px]">
                  {columnLeads.map((lead) => (
                    <GlassCard key={lead.id} className="p-4 border border-white/5 relative group" interactive>
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <h4 className="font-semibold text-white text-sm truncate w-36">{lead.name}</h4>
                          <span className="text-[10px] text-gray-400 mt-0.5 block truncate w-36">{lead.company}</span>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${lead.score >= 80 ? 'bg-rose-500/10 text-rose-400' : lead.score >= 50 ? 'bg-amber-500/10 text-amber-400' : 'bg-cyan-500/10 text-cyan-400'}`}>
                          {lead.grade || 'C'} ({lead.score})
                        </span>
                      </div>

                      {lead.details && (
                        <p className="text-[11px] text-gray-500 mt-3 border-t border-white/5 pt-2 leading-relaxed line-clamp-2">
                          {lead.details}
                        </p>
                      )}

                      {/* Controls and Actions */}
                      <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5 text-[10px] text-gray-500 font-semibold">
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => moveLead(lead, -1)}
                            disabled={COLUMNS.indexOf(column) === 0}
                            className="p-1 hover:text-white hover:bg-white/5 rounded disabled:opacity-30"
                          >
                            <ChevronLeft className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => moveLead(lead, 1)}
                            disabled={COLUMNS.indexOf(column) === COLUMNS.length - 1}
                            className="p-1 hover:text-white hover:bg-white/5 rounded disabled:opacity-30"
                          >
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => {
                              setName(lead.name);
                              setCompany(lead.company);
                              setScore(lead.score);
                              setGrade(lead.grade);
                              setDetails(lead.details);
                              setShowEditModal(lead);
                            }}
                            className="p-1 hover:text-white hover:bg-white/5 rounded"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteLead(lead.id)}
                            className="p-1 hover:text-red-400 hover:bg-red-500/10 rounded"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </GlassCard>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Lead Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <GlassCard className="w-full max-w-md border border-white/10 relative">
            <button 
              onClick={() => setShowAddModal(false)}
              className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white rounded-lg hover:bg-white/5"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-white mb-6">Create CRM Opportunity</h3>

            <form onSubmit={handleCreateLead} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Lead Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full glass-input"
                  placeholder="Johnathan Vance"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Company</label>
                <input
                  type="text"
                  required
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full glass-input"
                  placeholder="Acme Corp"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">BANT Score (0-100)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={score}
                    onChange={(e) => setScore(Number(e.target.value))}
                    className="w-full glass-input"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Lead Grade</label>
                  <select
                    value={grade}
                    onChange={(e) => setGrade(e.target.value)}
                    className="w-full glass-input"
                  >
                    <option value="A+">A+</option>
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Details / Notes</label>
                <textarea
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  rows="3"
                  className="w-full glass-input"
                  placeholder="Initial details and qualification reasoning..."
                ></textarea>
              </div>

              <button
                type="submit"
                className="w-full glass-button-primary mt-6 py-2"
              >
                Create Lead
              </button>
            </form>
          </GlassCard>
        </div>
      )}

      {/* Edit Lead Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <GlassCard className="w-full max-w-md border border-white/10 relative">
            <button 
              onClick={() => setShowEditModal(null)}
              className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white rounded-lg hover:bg-white/5"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-white mb-6">Modify CRM Opportunity</h3>

            <form onSubmit={handleEditLead} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Lead Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full glass-input"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Company</label>
                <input
                  type="text"
                  required
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full glass-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">BANT Score (0-100)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={score}
                    onChange={(e) => setScore(Number(e.target.value))}
                    className="w-full glass-input"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Lead Grade</label>
                  <select
                    value={grade}
                    onChange={(e) => setGrade(e.target.value)}
                    className="w-full glass-input"
                  >
                    <option value="A+">A+</option>
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-2">Details / Notes</label>
                <textarea
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  rows="3"
                  className="w-full glass-input"
                ></textarea>
              </div>

              <button
                type="submit"
                className="w-full glass-button-primary mt-6 py-2"
              >
                Save Changes
              </button>
            </form>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
