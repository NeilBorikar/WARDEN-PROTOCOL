import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import {
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Bot,
  Store,
  ShieldCheck,
  Send,
  Lock,
  Zap,
  ShieldAlert,
  Layers,
  Terminal,
  RefreshCw,
} from 'lucide-react';
import type { RunDetail } from '../../types/api';
import { api, DEMO_RUNS } from '../../api/client';
import { VerdictBadge } from '../common/VerdictBadge';
import { MoneyDisplay } from '../common/MoneyDisplay';
import { ProvenanceChip } from '../common/ProvenanceChip';

export const LiveRunScreen: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<'legit' | 'injection' | 'swap'>('legit');
  const [currentRun, setCurrentRun] = useState<RunDetail>(DEMO_RUNS['legit-purchase']);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(5);

  const cardsContainerRef = useRef<HTMLDivElement>(null);
  const decisionRef = useRef<HTMLDivElement>(null);

  const scenarioCards = [
    {
      id: 'legit' as const,
      title: 'Legitimate Procurement Order',
      desc: 'Autonomous Buyer orders approved office gear ($65.00). Triggers owner review above $50 threshold.',
      subtext: 'Fast Start • Standard Errand',
      expectedVerdict: 'ASK_OWNER',
      iconClass: 'nixtio-icon-orange',
      icon: Layers,
    },
    {
      id: 'injection' as const,
      title: 'Prompt Injection Override Attack',
      desc: 'Adversarial merchant attempts to hijack agent transcript and demand $850 offshore emergency fee.',
      subtext: 'Security Evaluation • Exploit Neutralized',
      expectedVerdict: 'BLOCK',
      iconClass: 'nixtio-icon-periwinkle',
      icon: Terminal,
    },
    {
      id: 'swap' as const,
      title: 'Business Email Compromise (BEC)',
      desc: 'Seller claims primary PayPal is down and redirects funds to unlisted evil offshore account.',
      subtext: 'Allowlist Defense • Account Spoofing Blocked',
      expectedVerdict: 'BLOCK',
      iconClass: 'nixtio-icon-indigo',
      icon: RefreshCw,
    },
  ];

  // GSAP: Animate cards on load
  useEffect(() => {
    if (cardsContainerRef.current) {
      gsap.from(cardsContainerRef.current.children, {
        opacity: 0,
        y: 18,
        stagger: 0.08,
        duration: 0.55,
        ease: 'power2.out',
      });
    }
  }, []);

  const handleRunScenario = async (scenario: 'legit' | 'injection' | 'swap') => {
    setIsLoading(true);
    setActiveStep(1);

    try {
      const data = await api.startRun({
        scenario_type: scenario,
        scripted: true,
      });

      let step = 1;
      const interval = setInterval(() => {
        step += 1;
        setActiveStep(step);
        if (step >= data.turns.length + 1) {
          clearInterval(interval);
          setIsLoading(false);
          setCurrentRun(data);
          
          if (decisionRef.current) {
            gsap.fromTo(decisionRef.current, { scale: 0.98 }, { scale: 1, duration: 0.35, ease: 'back.out(2)' });
          }
        }
      }, 400);
    } catch {
      setIsLoading(false);
      setCurrentRun(
        scenario === 'injection'
          ? DEMO_RUNS['prompt-injection']
          : scenario === 'swap'
          ? DEMO_RUNS['bank-swap']
          : DEMO_RUNS['legit-purchase']
      );
    }
  };

  useEffect(() => {
    handleRunScenario(selectedScenario);
  }, [selectedScenario]);

  return (
    <div className="space-y-6">
      {/* 3 Nixtio Feature Cards (Matching the reference image!) */}
      <div ref={cardsContainerRef} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {scenarioCards.map((sc) => {
          const isSelected = selectedScenario === sc.id;
          const Icon = sc.icon;

          return (
            <button
              key={sc.id}
              onClick={() => setSelectedScenario(sc.id)}
              className={`nixtio-card text-left p-5 flex flex-col justify-between cursor-pointer relative overflow-hidden transition-all ${
                isSelected
                  ? 'ring-2 ring-slate-900 border-transparent shadow-lg'
                  : 'hover:border-slate-300'
              }`}
            >
              <div>
                {/* Icon Box */}
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-10 h-10 rounded-2xl flex items-center justify-center ${sc.iconClass} shadow-2xs`}>
                    <Icon size={18} />
                  </div>
                  <VerdictBadge verdict={sc.expectedVerdict} size="sm" />
                </div>

                <h3 className="text-sm font-bold text-slate-900 leading-snug mb-1.5">
                  {sc.title}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed font-normal">
                  {sc.desc}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] font-semibold text-slate-400">
                <span>{sc.subtext}</span>
                {isSelected && (
                  <span className="w-2 h-2 rounded-full bg-slate-900 animate-pulse" />
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Main 2-Column AI Conversation & Verification Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Negotiation Transcript (7 cols) */}
        <div className="lg:col-span-7 nixtio-card overflow-hidden flex flex-col h-[520px]">
          {/* Header Bar */}
          <div className="px-5 py-4 bg-slate-50/70 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                <Bot size={16} />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Autonomous Multi-Agent Negotiation
                </h3>
                <span className="text-[10px] text-slate-400 font-medium">
                  Buyer LLM Agent vs. External Seller Stream
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleRunScenario(selectedScenario)}
                disabled={isLoading}
                className="nixtio-pill-dark px-3 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <RotateCcw size={12} className="animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <>
                    <Play size={12} className="fill-current" />
                    <span>Re-simulate</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Transcript Message Stream */}
          <div className="p-4 sm:p-5 space-y-3.5 overflow-y-auto flex-1 font-sans text-xs">
            {currentRun.turns.slice(0, activeStep).map((turn, idx) => {
              const isBuyer = turn.role === 'buyer';
              const isSeller = turn.role === 'seller';
              const isBouncer = turn.role === 'bouncer';

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-2xl border transition-all ${
                    isSeller
                      ? 'bg-slate-100/70 border-slate-200'
                      : isBuyer
                      ? 'bg-blue-50/50 border-blue-150'
                      : 'bg-indigo-50/60 border-indigo-150'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${
                        isSeller ? 'bg-slate-200 text-slate-800' : isBuyer ? 'bg-blue-100 text-blue-600' : 'bg-indigo-100 text-indigo-700'
                      }`}>
                        {isSeller ? <Store size={13} /> : isBuyer ? <Bot size={13} /> : <ShieldCheck size={13} />}
                      </div>
                      <span className="font-bold text-[11px] uppercase tracking-wider text-slate-900">
                        {turn.role}
                      </span>
                      {isSeller && (
                        <span className="px-2 py-0.2 rounded-full text-[9px] font-mono font-bold bg-slate-200 text-slate-800">
                          UNTRUSTED
                        </span>
                      )}
                      {isBuyer && (
                        <span className="px-2 py-0.2 rounded-full text-[9px] font-mono font-bold bg-blue-100 text-blue-700">
                          AUTONOMOUS_BUYER
                        </span>
                      )}
                      {isBouncer && (
                        <span className="px-2 py-0.2 rounded-full text-[9px] font-mono font-bold bg-indigo-100 text-indigo-700">
                          DETERMINISTIC_BOUNCER
                        </span>
                      )}
                    </div>

                    {turn.timestamp && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(turn.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    )}
                  </div>

                  <p className="text-slate-700 leading-relaxed break-words whitespace-pre-wrap">
                    {turn.message}
                  </p>

                  {/* Tool Call Box */}
                  {turn.tool_calls && turn.tool_calls.length > 0 && (
                    <div className="mt-2.5 rounded-xl bg-slate-900 text-slate-100 p-3 font-mono text-[11px] shadow-xs">
                      <div className="flex items-center justify-between text-blue-300 pb-1.5 border-b border-slate-800 mb-1.5 font-bold">
                        <div className="flex items-center gap-1.5">
                          <Send size={11} />
                          <span>Tool Call: {turn.tool_calls[0].name}</span>
                        </div>
                        <span className="text-[9px] text-slate-400 uppercase">Parameters</span>
                      </div>
                      <div className="space-y-1 text-slate-300">
                        {Object.entries(turn.tool_calls[0].arguments).map(([key, val]) => (
                          <div key={key} className="flex justify-between items-center py-0.5">
                            <span className="text-slate-400 font-mono">{key}:</span>
                            <span className="text-white font-medium">
                              {key.includes('minor') ? (
                                <MoneyDisplay amountMinor={val as number} />
                              ) : (
                                String(val)
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Footer Bar */}
          <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Lock size={12} className="text-blue-600" />
              Principle P1: Deterministic verification. Zero LLMs in payment path.
            </span>
            <span className="font-mono text-slate-500 uppercase font-bold">
              Run: {currentRun.run_id}
            </span>
          </div>
        </div>

        {/* Right Column: Bouncer Decision Engine (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Main Verdict & Policy Assessment Card */}
          <div ref={decisionRef} className="nixtio-card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center">
                  <ShieldCheck size={16} />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Bouncer Evaluation
                  </h3>
                  <span className="text-[10px] text-slate-400">Ed25519 Policy Enforcement</span>
                </div>
              </div>
              {currentRun.decision && (
                <VerdictBadge verdict={currentRun.decision.verdict} size="lg" />
              )}
            </div>

            {/* Proposed Payment Request Details Card */}
            {currentRun.payment_request ? (
              <div className="rounded-2xl bg-slate-50 border border-slate-200/80 p-4 space-y-2.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Proposed Payee:</span>
                  <span className="font-mono text-slate-900 font-bold truncate max-w-[200px]" title={currentRun.payment_request.payee.email}>
                    {currentRun.payment_request.payee.email}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Proposed Amount:</span>
                  <MoneyDisplay
                    amountMinor={currentRun.payment_request.amount_minor}
                    currency={currentRun.payment_request.currency}
                    className="text-base text-slate-900 font-extrabold"
                    showCurrency
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Errand Purpose:</span>
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-white text-slate-800 border border-slate-200">
                    {currentRun.payment_request.purpose}
                  </span>
                </div>

                {/* Provenance Tags Section */}
                <div className="pt-2 border-t border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                    Field Provenance Tags:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(currentRun.payment_request.provenance).map(([f, tag]) => (
                      <ProvenanceChip key={f} field={f} tag={tag} />
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                No payment request proposed yet.
              </div>
            )}

            {/* Decision Reasons List */}
            {currentRun.decision && (
              <div className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                  Enforcement Rationale:
                </span>
                <div className="space-y-2">
                  {currentRun.decision.reasons.map((r, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] text-blue-600 font-bold">
                          Check {r.check_id}
                        </span>
                        <span className="font-mono text-[9px] text-slate-400 font-semibold">
                          {r.code}
                        </span>
                      </div>
                      <p className="text-slate-700 text-[11px] leading-relaxed">
                        {r.message}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Rail Execution Card (Zero Greens/Reds) */}
          <div className="nixtio-card p-4 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Zap size={14} className="text-blue-500" />
              PayPal Rail Execution
            </h4>
            
            {currentRun.payment_executed ? (
              <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl flex items-center gap-3 text-xs text-blue-950">
                <div className="w-8 h-8 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                  <CheckCircle2 size={18} />
                </div>
                <div>
                  <span className="font-bold block text-blue-950">
                    Payout Dispatched via PayPal Rail
                  </span>
                  <span className="font-mono text-[11px] text-blue-700 font-semibold">
                    Tx ID: {currentRun.rail_payment_id || 'PAYPAL-MOCK-TX-4921'}
                  </span>
                </div>
              </div>
            ) : currentRun.decision?.verdict === 'ASK_OWNER' ? (
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-2xl flex items-center gap-3 text-xs text-amber-900">
                <div className="w-8 h-8 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 shrink-0">
                  <AlertTriangle size={18} />
                </div>
                <div>
                  <span className="font-bold block text-amber-950">
                    Awaiting Owner Ed25519 Token
                  </span>
                  <span className="text-[11px] text-amber-700 leading-snug">
                    Threshold exceeded ($50). Spend halted until owner authorizes in Approvals queue.
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3.5 bg-slate-100 border border-slate-200 rounded-2xl flex items-center gap-3 text-xs text-slate-900">
                <div className="w-8 h-8 rounded-xl bg-slate-200 flex items-center justify-center text-slate-800 shrink-0">
                  <ShieldAlert size={18} />
                </div>
                <div>
                  <span className="font-bold block text-slate-950">
                    Funds Secured (Loss: $0.00)
                  </span>
                  <span className="text-[11px] text-slate-600 leading-snug">
                    Transaction rejected. Agent was blocked from accessing PayPal credentials.
                  </span>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};
