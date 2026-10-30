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
      icon: KeyRound,
      variant: 'bg-white border-slate-300 text-slate-900',
    },
    VERIFIED_RECORD: {
      label: 'VERIFIED',
      desc: 'Cryptographically validated against standing mandate or intent',
      icon: ShieldCheck,
      variant: 'bg-white border-slate-200 text-slate-800',
    },
    AGENT_DERIVED: {
      label: 'AGENT_DERIVED',
      desc: 'Synthesized by untrusted AI agent conversational reasoning',
      icon: Cpu,
      variant: 'bg-slate-50 border-slate-200 text-slate-600',
    },
    UNTRUSTED_EXTERNAL: {
      label: 'UNTRUSTED_EXTERNAL',
      desc: 'Extracted from untrusted merchant or external party prompt',
      icon: AlertOctagon,
      variant: 'bg-slate-100 border-slate-300 text-slate-900 font-extrabold',
    },
  }[norm] || {
    label: norm,
    desc: 'Provenance source uncertified',
    icon: AlertOctagon,
    variant: 'bg-slate-50 border-slate-200 text-slate-700',
  };

  const Icon = config.icon;

  return (
    <span
      tabIndex={0}
      role="note"
      aria-label={`${field ? `${field}: ` : ''}${config.label} — ${config.desc}`}
      title={`${field ? `${field}: ` : ''}${config.desc}`}
      className={`group relative inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono border shadow-2xs cursor-help transition-all hover:border-slate-400 ${config.variant} ${className}`}
    >
      <Icon size={11} className="shrink-0 stroke-[2.2]" aria-hidden="true" />
      <span>{field ? <span className="opacity-60 font-normal mr-1">{field}:</span> : null}{config.label}</span>
    </span>
  );
};
