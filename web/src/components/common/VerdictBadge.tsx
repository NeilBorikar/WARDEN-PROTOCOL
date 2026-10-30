import React from 'react';
import { Check, Hourglass, ShieldOff } from 'lucide-react';
import type { Verdict } from '../../types/api';

interface VerdictBadgeProps {
  verdict: Verdict | string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  animate?: boolean;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  verdict,
  size = 'md',
  className = '',
  animate = true,
}) => {
  const norm = String(verdict).toUpperCase();

  const sizeClasses = {
    sm: 'px-2.5 py-0.5 text-[10px] gap-1.5 font-medium',
    md: 'px-3 py-1 text-xs font-semibold gap-1.5',
    lg: 'px-4 py-1.5 text-sm font-bold gap-2',
  }[size];

  const iconSizes = {
    sm: 11,
    md: 13,
    lg: 15,
  }[size];

  const animClass = animate ? 'animate-chip-pop' : '';

  // ALLOW: check icon, outlined pill (Zero reliance on color)
  if (norm === 'ALLOW') {
    return (
      <span
        role="status"
        aria-label="Verdict ALLOW: Payment Approved"
        className={`inline-flex items-center rounded-full bg-white text-slate-800 border border-slate-300 font-mono shadow-2xs tracking-wider ${sizeClasses} ${animClass} ${className}`}
      >
        <Check size={iconSizes} className="shrink-0 stroke-[2.5]" aria-hidden="true" />
        <span>ALLOW</span>
      </span>
    );
  }

  // ASK_OWNER: hourglass icon, dashed-outline pill
  if (norm === 'ASK_OWNER') {
    return (
      <span
        role="status"
        aria-label="Verdict ASK_OWNER: Escalated to Owner"
        className={`inline-flex items-center rounded-full bg-slate-50/80 text-slate-800 border border-dashed border-slate-400 font-mono shadow-2xs tracking-wider ${sizeClasses} ${animClass} ${className}`}
      >
        <Hourglass size={iconSizes} className="shrink-0 animate-spin-slow stroke-[2]" aria-hidden="true" />
        <span>ASK_OWNER</span>
      </span>
    );
  }

  // BLOCK: shield-slash icon, solid-filled pill (accent token) with bolder weight
  return (
    <span
      role="status"
      aria-label="Verdict BLOCK: Payment Blocked"
      className={`inline-flex items-center rounded-full bg-slate-900 text-white font-mono font-black shadow-sm tracking-wider ${sizeClasses} ${animClass} ${className}`}
    >
      <ShieldOff size={iconSizes} className="shrink-0 text-slate-200 stroke-[2.5]" aria-hidden="true" />
      <span>BLOCK</span>
    </span>
  );
};
