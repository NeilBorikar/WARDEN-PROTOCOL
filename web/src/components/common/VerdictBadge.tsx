import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
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
    sm: 'px-2 py-0.5 text-[11px] gap-1 font-semibold',
    md: 'px-3 py-1 text-xs font-bold gap-1.5',
    lg: 'px-4 py-1.5 text-sm font-extrabold gap-2',
  }[size];

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  }[size];

  if (norm === 'ALLOW') {
    return (
      <span
        role="status"
        aria-label="Verdict ALLOW: Payment Approved"
        className={`inline-flex items-center rounded-full bg-emerald-500/10 dark:bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 dark:border-emerald-500/40 font-mono shadow-xs shadow-emerald-500/10 ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <CheckCircle2 size={iconSizes} className="shrink-0 text-emerald-500" aria-hidden="true" />
        <span className="tracking-wide">ALLOW</span>
      </span>
    );
  }

  if (norm === 'ASK_OWNER') {
    return (
      <span
        role="status"
        aria-label="Verdict ASK_OWNER: Escalated to Owner Approval"
        className={`inline-flex items-center rounded-full bg-amber-500/10 dark:bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 dark:border-amber-500/40 font-mono shadow-xs shadow-amber-500/10 ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
        <AlertTriangle size={iconSizes} className="shrink-0 text-amber-500" aria-hidden="true" />
        <span className="tracking-wide">ASK_OWNER</span>
      </span>
    );
  }

  // Default to BLOCK for security fail-closed
  return (
    <span
      role="status"
      aria-label="Verdict BLOCK: Payment Rejected by Bouncer"
      className={`inline-flex items-center rounded-full bg-rose-500/10 dark:bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 dark:border-rose-500/40 font-mono shadow-xs shadow-rose-500/10 ${sizeClasses} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
      <ShieldAlert size={iconSizes} className="shrink-0 text-rose-500" aria-hidden="true" />
      <span className="tracking-wide">BLOCK</span>
    </span>
  );
};
