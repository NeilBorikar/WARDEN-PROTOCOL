import React from 'react';
import { AlertCircle, KeyRound, Store, UserCheck, Clock } from 'lucide-react';

export const ResidualRisks: React.FC = () => {
  const risks = [
    {
      title: 'Owner Private Key Compromise',
      desc: "If an adversary exfiltrates the owner's Ed25519 private key, they can sign forged spending mandates and intents with mathematical validity.",
      icon: KeyRound,
      mitigation: 'Hardware enclave keystore & air-gapped signing policies.',
    },
    {
      title: 'Colluding Allowlisted Merchant',
      desc: 'An approved vendor that turns malicious can charge up to the single-transaction cap ($100) and cumulative daily limit ($500) before revocation.',
      icon: Store,
      mitigation: 'Real-time velocity limits, dispute webhooks, and manual allowlist removal.',
    },
    {
      title: 'Careless Owner Escalation Approval',
      desc: 'If an owner authorizes an escalated ASK_OWNER request without inspecting the plain-English trigger rationale, fraudulent funds may settle.',
      icon: UserCheck,
      mitigation: '15-minute single-use TTL expiry & hold-to-confirm cryptographic gating.',
    },
    {
      title: 'Sandbox OAuth Token Expiry',
      desc: 'PayPal sandbox bearer tokens expire after 9 hours of continuous uptime under autonomous multi-day execution scenarios.',
      icon: Clock,
      mitigation: 'Automated background refresh pipeline with fake-clock deterministic test harness.',
    },
  ];

  return (
    <div className="nixtio-card p-5 sm:p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-150 pb-3">
        <div className="flex items-center gap-2">
          <AlertCircle size={16} className="text-slate-800" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
            Honest Limitations & Residual Risks (Principle P7)
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-400">
          STRIDE Threat Model Compliance
        </span>
      </div>

      <p className="text-xs text-slate-500 leading-relaxed">
        Per Principle P7 (<em>"Never claim unbreakable; state residual risks in the threat model"</em>), the Bouncer enforces deterministic bounds on autonomous spending, but operates under explicit threat boundaries:
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
        {risks.map((r, i) => {
          const Icon = r.icon;
          return (
            <div
              key={i}
              className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-xs"
            >
              <div className="flex items-center gap-2 text-slate-900 font-bold">
                <div className="w-6 h-6 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0">
                  <Icon size={13} className="text-slate-700" />
                </div>
                <span>{r.title}</span>
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed font-sans">
                {r.desc}
              </p>
              <div className="pt-1.5 border-t border-slate-200/80 text-[10px] font-mono text-slate-500">
                <span className="font-semibold text-slate-700">Mitigation: </span>
                {r.mitigation}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
