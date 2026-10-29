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
      color: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      icon: KeyRound,
    },
    VERIFIED_RECORD: {
      label: 'VERIFIED',
      desc: 'Validated against owner-signed mandate or intent',
      color: 'bg-blue-50 text-blue-700 border-blue-200',
      icon: ShieldCheck,
    },
    AGENT_DERIVED: {
      label: 'AGENT',
      desc: 'Synthesized by AI agent reasoning',
      color: 'bg-sky-50 text-sky-700 border-sky-200',
      icon: Cpu,
    },
    UNTRUSTED_EXTERNAL: {
      label: 'UNTRUSTED',
      desc: 'Received from untrusted seller/external chat transcript',
      color: 'bg-slate-100 text-slate-800 border-slate-300',
      icon: AlertOctagon,
    },
  }[norm] || {
    label: norm,
    desc: 'Unknown provenance',
    color: 'bg-slate-50 text-slate-700 border-slate-200',
    icon: AlertOctagon,
  };

  const Icon = config.icon;

  return (
    <span
      title={`${field ? `${field}: ` : ''}${config.desc}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border shadow-2xs ${config.color} ${className}`}
    >
      <Icon size={11} className="shrink-0" aria-hidden="true" />
      <span>{field ? <span className="opacity-70 font-normal">{field}: </span> : null}{config.label}</span>
    </span>
  );
};
