import React from 'react';
import { CheckCircle2, AlertTriangle, Shield } from 'lucide-react';
import type { Verdict } from '../../types/api';

interface VerdictBadgeProps {
  verdict: Verdict | string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  verdict,
  size = 'md',
  className = '',
}) => {
  const norm = String(verdict).toUpperCase();

  const sizeClasses = {
    sm: 'px-2.5 py-0.5 text-[10px] gap-1.5 font-bold',
    md: 'px-3 py-1 text-xs font-bold gap-1.5',
    lg: 'px-4 py-1.5 text-sm font-extrabold gap-2',
  }[size];

  const iconSizes = {
    sm: 11,
    md: 13,
    lg: 15,
  }[size];

  if (norm === 'ALLOW') {
    return (
      <span
        role="status"
        aria-label="Verdict ALLOW: Payment Approved"
        className={`inline-flex items-center rounded-full bg-blue-50 text-blue-700 border border-blue-200/90 font-mono shadow-2xs ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
        <CheckCircle2 size={iconSizes} className="shrink-0 text-blue-600" aria-hidden="true" />
        <span className="tracking-wide">ALLOW</span>
      </span>
    );
  }

  if (norm === 'ASK_OWNER') {
    return (
      <span
        role="status"
        aria-label="Verdict ASK_OWNER: Escalated to Owner Approval"
        className={`inline-flex items-center rounded-full bg-amber-50 text-amber-800 border border-amber-200/90 font-mono shadow-2xs ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse" />
        <AlertTriangle size={iconSizes} className="shrink-0 text-amber-600" aria-hidden="true" />
        <span className="tracking-wide">ASK_OWNER</span>
      </span>
    );
  }

  // Default to BLOCK for security fail-closed (Sleek Obsidian/Dark Slate Pill - No red)
  return (
    <span
      role="status"
      aria-label="Verdict BLOCK: Payment Intercepted by Bouncer"
      className={`inline-flex items-center rounded-full bg-slate-900 text-white font-mono shadow-2xs ${sizeClasses} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
      <Shield size={iconSizes} className="shrink-0 text-slate-300" aria-hidden="true" />
      <span className="tracking-wide">BLOCK</span>
    </span>
  );
};
