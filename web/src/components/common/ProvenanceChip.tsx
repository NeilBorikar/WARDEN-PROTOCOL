import React from 'react';
import { KeyRound, ShieldCheck, Cpu, AlertOctagon } from 'lucide-react';
import type { ProvenanceTag } from '../../types/api';

interface ProvenanceChipProps {
  tag: ProvenanceTag | string;
  field?: string;
  className?: string;
}

export const ProvenanceChip: React.FC<ProvenanceChipProps> = ({
  tag,
  field,
  className = '',
}) => {
  const norm = String(tag).toUpperCase();

  const config = {
    OWNER: {
      label: 'OWNER',
      desc: 'Signed directly with owner Ed25519 private key',
      color: 'bg-indigo-500/10 dark:bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border-indigo-500/30',
      icon: KeyRound,
    },
    VERIFIED_RECORD: {
      label: 'VERIFIED',
      desc: 'Validated against owner-signed mandate or intent',
      color: 'bg-emerald-500/10 dark:bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border-emerald-500/30',
      icon: ShieldCheck,
    },
    AGENT_DERIVED: {
      label: 'AGENT',
      desc: 'Synthesized by AI agent reasoning',
      color: 'bg-cyan-500/10 dark:bg-cyan-500/15 text-cyan-600 dark:text-cyan-300 border-cyan-500/30',
      icon: Cpu,
    },
    UNTRUSTED_EXTERNAL: {
      label: 'UNTRUSTED',
      desc: 'Received from untrusted seller/external chat transcript',
      color: 'bg-rose-500/10 dark:bg-rose-500/15 text-rose-600 dark:text-rose-300 border-rose-500/30',
      icon: AlertOctagon,
    },
  }[norm] || {
    label: norm,
    desc: 'Unknown provenance',
    color: 'bg-slate-500/10 dark:bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/30',
    icon: AlertOctagon,
  };

  const Icon = config.icon;

  return (
    <span
      title={`${field ? `${field}: ` : ''}${config.desc}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-medium border shadow-2xs ${config.color} ${className}`}
    >
      <Icon size={12} className="shrink-0" aria-hidden="true" />
      <span>{field ? <span className="opacity-75 font-normal">{field}: </span> : null}{config.label}</span>
    </span>
  );
};
