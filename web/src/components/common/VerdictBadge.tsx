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
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-xs font-semibold gap-1.5',
    lg: 'px-3.5 py-1.5 text-sm font-bold gap-2',
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
        className={`inline-flex items-center rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono ${sizeClasses} ${className}`}
      >
        <CheckCircle2 size={iconSizes} className="shrink-0 text-emerald-400" aria-hidden="true" />
        <span>ALLOW</span>
      </span>
    );
  }

  if (norm === 'ASK_OWNER') {
    return (
      <span
        role="status"
        aria-label="Verdict ASK_OWNER: Escalated to Owner Approval"
        className={`inline-flex items-center rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-mono ${sizeClasses} ${className}`}
      >
        <AlertTriangle size={iconSizes} className="shrink-0 text-amber-400" aria-hidden="true" />
        <span>ASK_OWNER</span>
      </span>
    );
  }

  // Default to BLOCK for security fail-closed
  return (
    <span
      role="status"
      aria-label="Verdict BLOCK: Payment Rejected by Bouncer"
      className={`inline-flex items-center rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 font-mono ${sizeClasses} ${className}`}
    >
      <ShieldAlert size={iconSizes} className="shrink-0 text-rose-400" aria-hidden="true" />
      <span>BLOCK</span>
    </span>
  );
};
