import React, { useState, useEffect } from 'react';
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
  Sparkles,
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

  const scenarioOptions = [
    {
      id: 'legit' as const,
      title: 'Legitimate Procurement',
      desc: 'Office gear order ($65.00) triggers owner approval ($50 threshold)',
      expectedVerdict: 'ASK_OWNER',
    },
    {
      id: 'injection' as const,
      title: 'Prompt Injection Override',
      desc: 'Adversarial seller injects $850 offshore override into transcript',
      expectedVerdict: 'BLOCK',
    },
    {
      id: 'swap' as const,
      title: 'Bank-Detail Swap (BEC)',
      desc: 'Seller claims payment routing update to unlisted evil account',
      expectedVerdict: 'BLOCK',
    },
  ];

  const handleRunScenario = async (scenario: 'legit' | 'injection' | 'swap') => {
    setIsLoading(true);
    setActiveStep(1);

    try {
      const data = await api.startRun({
        scenario_type: scenario,
        scripted: true,
      });

      // Animate turns sequentially for realistic simulation
      let step = 1;
      const interval = setInterval(() => {
        step += 1;
        setActiveStep(step);
        if (step >= data.turns.length + 1) {
          clearInterval(interval);
          setIsLoading(false);
          setCurrentRun(data);
        }
      }, 500);
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
      {/* Top Banner & Scenario Selector */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                Live Negotiation & Decision Timeline
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Watch the Buyer agent negotiate with the Seller. Money can only leave after the Bouncer verifies
              the proposed deal against owner-signed Mandate & Intent constraints.
            </p>
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <button
              onClick={() => handleRunScenario(selectedScenario)}
              disabled={isLoading}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer w-full md:w-auto"
            >
              {isLoading ? (
                <>
                  <RotateCcw size={14} className="animate-spin" />
                  <span>Evaluating Bouncer Checks...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Re-run Scenario</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Scenario Tabs */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-800">
          {scenarioOptions.map((sc) => {
            const isSelected = selectedScenario === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => setSelectedScenario(sc.id)}
                className={`text-left p-3 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-blue-600/10 border-blue-500/50 shadow-sm'
                    : 'bg-slate-800/50 border-slate-700/60 hover:bg-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-semibold ${isSelected ? 'text-blue-400' : 'text-slate-200'}`}>
                    {sc.title}
                  </span>
                  <VerdictBadge verdict={sc.expectedVerdict} size="sm" />
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">{sc.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Negotiation Transcript (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm flex flex-col h-[680px]">
          <div className="px-5 py-3.5 bg-slate-800/50 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-cyan-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Agent Transcript (Buyer & Seller)
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-slate-400">
                Run ID: <span className="text-slate-200">{currentRun.run_id}</span>
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                Max 8 Turns
              </span>
            </div>
          </div>

          <div className="p-4 space-y-4 overflow-y-auto flex-1 font-sans text-sm">
            {currentRun.turns.slice(0, activeStep).map((turn, idx) => {
              const isBuyer = turn.role === 'buyer';
              const isSeller = turn.role === 'seller';
              const isVerifier = turn.role === 'verifier';
              const isBouncer = turn.role === 'bouncer';

              return (
                <div
                  key={idx}
                  className={`flex gap-3 p-3.5 rounded-lg border transition-all ${
                    isSeller
                      ? 'bg-rose-950/20 border-rose-900/30'
                      : isBuyer
                      ? 'bg-blue-950/20 border-blue-900/30'
                      : isVerifier
                      ? 'bg-amber-950/20 border-amber-900/30'
                      : 'bg-emerald-950/20 border-emerald-900/30'
                  }`}
                >
                  <div className="shrink-0 mt-0.5">
                    {isSeller && (
                      <div className="w-7 h-7 rounded-full bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
                        <Store size={14} />
                      </div>
                    )}
                    {isBuyer && (
                      <div className="w-7 h-7 rounded-full bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
                        <Bot size={14} />
                      </div>
                    )}
                    {isVerifier && (
                      <div className="w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
                        <Sparkles size={14} />
                      </div>
                    )}
                    {isBouncer && (
                      <div className="w-7 h-7 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                        <ShieldCheck size={14} />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                          {turn.role}
                        </span>
                        {isSeller && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            UNTRUSTED_EXTERNAL
                          </span>
                        )}
                        {isBuyer && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30">
                            AUTONOMOUS_BUYER
                          </span>
                        )}
                      </div>
                      {turn.timestamp && (
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(turn.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <p className="text-xs text-slate-300 leading-relaxed break-words whitespace-pre-wrap">
                      {turn.message}
                    </p>

                    {/* Tool Call Card */}
                    {turn.tool_calls && turn.tool_calls.length > 0 && (
                      <div className="mt-2 bg-slate-950/80 border border-slate-800 rounded p-2.5 font-mono text-xs">
                        <div className="flex items-center gap-1.5 text-blue-400 mb-1.5">
                          <Send size={12} />
                          <span className="font-semibold">Tool Call: {turn.tool_calls[0].name}</span>
                        </div>
                        <div className="space-y-1 text-slate-400 text-[11px]">
                          {Object.entries(turn.tool_calls[0].arguments).map(([key, val]) => (
                            <div key={key} className="flex justify-between border-b border-slate-900 pb-0.5">
                              <span className="text-slate-400">{key}:</span>
                              <span className="text-slate-200 font-medium">
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
                </div>
              );
            })}
          </div>

          <div className="px-4 py-2.5 bg-slate-950 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Lock size={12} className="text-emerald-400" />
              Principle P1: Deterministic Bouncer enforces checks. No LLM in payment path.
            </span>
            <span className="font-mono text-slate-400">Status: {currentRun.status}</span>
          </div>
        </div>

        {/* Right Column: Bouncer Decision Timeline (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Main Verdict Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-blue-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Bouncer Evaluation
                </h3>
              </div>
              {currentRun.decision && (
                <VerdictBadge verdict={currentRun.decision.verdict} size="lg" />
              )}
            </div>

            {/* Proposed Payment Request Details */}
            {currentRun.payment_request ? (
              <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-2.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Proposed Payee:</span>
                  <span className="font-mono text-slate-200 font-semibold truncate max-w-[200px]" title={currentRun.payment_request.payee.email}>
                    {currentRun.payment_request.payee.email}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Proposed Amount:</span>
                  <MoneyDisplay
                    amountMinor={currentRun.payment_request.amount_minor}
                    currency={currentRun.payment_request.currency}
                    className="text-white font-bold"
                    showCurrency
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Erran Purpose:</span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300">
                    {currentRun.payment_request.purpose}
                  </span>
                </div>

                {/* Provenance Tags */}
                <div className="pt-2 border-t border-slate-900">
                  <span className="text-[11px] text-slate-400 block mb-1.5">Field Provenance Tags:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(currentRun.payment_request.provenance).map(([f, tag]) => (
                      <ProvenanceChip key={f} field={f} tag={tag} />
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 text-center text-xs text-slate-400 bg-slate-950/40 rounded-lg border border-dashed border-slate-800">
                No payment request proposed yet.
              </div>
            )}

            {/* Decision Reasons List */}
            {currentRun.decision && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">
                  Enforcement Reasons:
                </span>
                <div className="space-y-2">
                  {currentRun.decision.reasons.map((r, i) => (
                    <div
                      key={i}
                      className="p-2.5 rounded bg-slate-950 border border-slate-800 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] text-blue-400 font-bold">
                          Check {r.check_id}
                        </span>
                        <span className="font-mono text-[10px] text-slate-400">
                          {r.code}
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        {r.message}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Cryptographic Hashes */}
            {currentRun.decision && (
              <div className="pt-2 border-t border-slate-800 space-y-1 font-mono text-[10px] text-slate-400">
                <div className="flex justify-between truncate">
                  <span>Mandate Hash:</span>
                  <span className="text-slate-400">{currentRun.decision.mandate_hash.slice(0, 16)}...</span>
                </div>
                <div className="flex justify-between truncate">
                  <span>Request Hash:</span>
                  <span className="text-slate-400">{currentRun.decision.request_hash.slice(0, 16)}...</span>
                </div>
              </div>
            )}
          </div>

          {/* Outcome & Rail Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              PayPal Rail Execution
            </h4>
            {currentRun.payment_executed ? (
              <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-lg flex items-center gap-2.5 text-xs text-emerald-300">
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                <div>
                  <span className="font-semibold block">Payout Dispatched via PayPal Rail</span>
                  <span className="font-mono text-[11px] text-emerald-400">
                    ID: {currentRun.rail_payment_id || 'PAYPAL-MOCK-TX-4921'}
                  </span>
                </div>
              </div>
            ) : currentRun.decision?.verdict === 'ASK_OWNER' ? (
              <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg flex items-center gap-2.5 text-xs text-amber-300">
                <AlertTriangle size={16} className="text-amber-400 shrink-0" />
                <div>
                  <span className="font-semibold block">Awaiting Owner Approval</span>
                  <span className="text-[11px] text-amber-400">
                    Money will not move until owner signs single-use token in Approvals tab.
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-lg flex items-center gap-2.5 text-xs text-rose-300">
                <Lock size={16} className="text-rose-400 shrink-0" />
                <div>
                  <span className="font-semibold block">Money Retained Safely</span>
                  <span className="text-[11px] text-rose-400">
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
