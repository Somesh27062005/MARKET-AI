import React from 'react';

export default function GlassCard({ children, className = '', interactive = false, ...props }) {
  const baseClass = interactive ? 'glass-panel-interactive' : 'glass-panel';
  return (
    <div 
      className={`${baseClass} rounded-2xl p-6 ${className}`} 
      {...props}
    >
      {children}
    </div>
  );
}
