import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, X, Sparkles, Loader2 } from 'lucide-react';
import GlassCard from './GlassCard.jsx';

export default function ChatAssistant({ domain, contextData, getCsrfToken }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Configuration for domains
  const domainConfig = {
    campaign: {
      title: 'Campaign Copilot',
      welcome: "Hello! I'm your Campaign Strategist. Ask me about the generated target persona, channel strategies, budget allocations, or ad copies.",
      hints: ['Explain the budget split', 'Refine the target persona', 'Draft another LinkedIn ad']
    },
    pitch: {
      title: 'Pitch Enablement Coach',
      welcome: "Hi! I'm your Sales Coach. Ask me about objection handling scripts, custom cold outreach templates, or discovery questions.",
      hints: ['How to handle pricing objections?', 'Draft a custom cold email', 'Detail proposal outline']
    },
    lead: {
      title: 'Lead Score Assistant',
      welcome: "Hello! I'm your Lead Qualification Assistant. Ask me to analyze Sarah's fit, explain the BANT criteria, or detail the next best action.",
      hints: ['What is the next best action?', 'Explain the need fit score', 'How to handle budget constraints?']
    },
    market: {
      title: 'Market Intelligence Analyst',
      welcome: "Hi! I'm your Market Analyst. Ask me about SWOT quadrants, PESTEL factors, competitor details, or growth drivers.",
      hints: ['Summarize competitor weaknesses', 'Explain Opportunities quadrant', 'Detail PESTEL technological trends']
    },
    insights: {
      title: 'Strategy Advisory Advisor',
      welcome: "Hello! I'm your Strategic Advisor. Ask me about the 30/60/90 action plan, root cause diagnostics, or cost optimization areas.",
      hints: ['Detail the Day 1-30 plan', 'How to optimize operational costs?', 'What is the root cause diagnosis?']
    }
  };

  const config = domainConfig[domain] || {
    title: 'AI Copilot',
    welcome: 'Hello! I am your business assistant. How can I help you today?',
    hints: ['Summarize the report', 'What are key action items?']
  };

  // Initialize messages on domain load
  useEffect(() => {
    setMessages([
      { role: 'assistant', content: config.welcome }
    ]);
  }, [domain]);

  // Scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim()) return;

    // Add user message
    const userMsg = { role: 'user', content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/v2/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          message: text,
          history: messages.map(m => ({ role: m.role, content: m.content })),
          domain,
          context_data: contextData
        })
      });

      const data = await response.json();
      if (response.ok && data.success) {
        setMessages([...newMessages, { role: 'assistant', content: data.response }]);
      } else {
        setMessages([...newMessages, { role: 'assistant', content: data.error || 'Failed to get a response. Please try again.' }]);
      }
    } catch (err) {
      console.error(err);
      setMessages([...newMessages, { role: 'assistant', content: 'Connection error. Please verify the server is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessageContent = (text, role) => {
    if (!text) return '';
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      let content = line;
      const isBullet = line.trim().startsWith('- ') || line.trim().startsWith('* ');
      if (isBullet) {
        content = line.trim().substring(2);
      }

      // Convert **bold** to strong
      const boldRegex = /\*\*(.*?)\*\*/g;
      const parts = [];
      let lastIndex = 0;
      let match;
      while ((match = boldRegex.exec(content)) !== null) {
        if (match.index > lastIndex) {
          parts.push(content.substring(lastIndex, match.index));
        }
        parts.push(<strong key={match.index} className="font-bold text-current">{match[1]}</strong>);
        lastIndex = boldRegex.lastIndex;
      }
      if (lastIndex < content.length) {
        parts.push(content.substring(lastIndex));
      }

      const renderedContent = parts.length > 0 ? parts : content;

      if (isBullet) {
        return (
          <li key={idx} className="list-disc list-inside ml-2 text-xs my-0.5 text-current">
            {renderedContent}
          </li>
        );
      }

      return (
        <p key={idx} className="text-xs leading-relaxed my-0.5 min-h-[1em] text-current">
          {renderedContent}
        </p>
      );
    });
  };

  return (
    <>
      {/* Floating Chat Bubble */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 p-4 rounded-full bg-indigo-600 text-white shadow-xl hover:scale-105 hover:bg-indigo-500 transition-all duration-300 border border-white/10 flex items-center justify-center cursor-pointer"
      >
        {isOpen ? <X className="w-6 h-6 animate-spin-slow" /> : <MessageSquare className="w-6 h-6" />}
      </button>

      {/* Expanded Chat Pane */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 w-96 h-[500px] z-50 rounded-2xl border border-slate-200 glass-panel shadow-2xl flex flex-col overflow-hidden animate-fade-in bg-white/95 backdrop-blur-xl">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50/50">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-sm font-bold text-slate-800 tracking-wide">{config.title}</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3 border ${
                    msg.role === 'user'
                      ? 'chat-user-message rounded-tr-none text-white'
                      : 'chat-assistant-message rounded-tl-none text-slate-800'
                  }`}
                >
                  {renderMessageContent(msg.content, msg.role)}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="chat-assistant-message rounded-2xl rounded-tl-none p-3 border flex items-center space-x-2 text-slate-700">
                  <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
                  <span className="text-[10px] text-slate-500">Copilot thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Suggestions */}
          {messages.length === 1 && !loading && (
            <div className="px-4 pb-2.5 pt-2 flex flex-wrap gap-1.5 bg-slate-50 border-t border-slate-100">
              {config.hints.map((hint, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(hint)}
                  className="chat-suggestion-chip text-[10px] font-semibold px-2.5 py-1.5 rounded-lg transition-all cursor-pointer"
                >
                  {hint}
                </button>
              ))}
            </div>
          )}

          {/* Input Footer */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-3 border-t border-slate-100 bg-slate-50 flex items-center space-x-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a clarifying question..."
              className="flex-1 glass-input py-1.5 px-3 text-xs bg-white border border-slate-200 text-slate-900 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-all flex items-center justify-center cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
