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
      desc: 'Signed directly with owner private key',
      color: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
      icon: KeyRound,
    },
    VERIFIED_RECORD: {
      label: 'VERIFIED',
      desc: 'Validated against owner-signed mandate or intent',
      color: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
      icon: ShieldCheck,
    },
    AGENT_DERIVED: {
      label: 'AGENT',
      desc: 'Synthesized by AI agent logic',
      color: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
      icon: Cpu,
    },
    UNTRUSTED_EXTERNAL: {
      label: 'UNTRUSTED',
      desc: 'Received from untrusted seller/external chat',
      color: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
      icon: AlertOctagon,
    },
  }[norm] || {
    label: norm,
    desc: 'Unknown provenance',
    color: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    icon: AlertOctagon,
  };

  const Icon = config.icon;

  return (
    <span
      title={`${field ? `${field}: ` : ''}${config.desc}`}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono border ${config.color} ${className}`}
    >
      <Icon size={12} className="shrink-0" aria-hidden="true" />
      <span>{field ? `${field}: ` : ''}{config.label}</span>
    </span>
  );
};
