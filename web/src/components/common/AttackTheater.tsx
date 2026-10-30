import React, { useState, useRef } from 'react';
import gsap from 'gsap';
import { Play, RotateCcw, Shield, Bot, ShieldOff, Check, X, AlertCircle, Volume2, VolumeX } from 'lucide-react';
import { REPLAY_BANK_SWAP } from '../../demo/attackReplay';
import { VerdictBadge } from './VerdictBadge';
import { sounds } from '../../utils/audio';

export const AttackTheater: React.FC = () => {
  const scenario = REPLAY_BANK_SWAP;
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [activeCheckIndex, setActiveCheckIndex] = useState<number>(-1);
  const [stamped, setStamped] = useState<boolean>(false);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(false);

  const stampRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleSound = () => {
    sounds.enabled = !soundEnabled;
    setSoundEnabled(!soundEnabled);
  };

  const handleRunAttack = () => {
    if (isRunning) return;
    setIsRunning(true);
    setActiveCheckIndex(-1);
    setStamped(false);

    // Sequence: 8 checks tick through sequentially (140ms per check)
    let currentIdx = 0;
    const interval = setInterval(() => {
      setActiveCheckIndex(currentIdx);
      currentIdx++;

      if (currentIdx >= scenario.checks.length) {
        clearInterval(interval);
        setTimeout(() => {
          setStamped(true);
          setIsRunning(false);
          sounds.playBlockStamp();

          if (stampRef.current) {
            gsap.fromTo(
              stampRef.current,
              { scale: 1.8, opacity: 0, rotate: -8 },
              { scale: 1, opacity: 1, rotate: 0, duration: 0.35, ease: 'back.out(2)' }
            );
          }
        }, 300);
      }
    }, 140);
  };

  const handleReset = () => {
    setIsRunning(false);
    setActiveCheckIndex(-1);
    setStamped(false);
  };

  return (
    <div ref={containerRef} className="nixtio-card p-5 sm:p-6 space-y-5">
      {/* Top Header Row with prominent [REPLAY] badge & sound toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-150">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl nixtio-icon-slate flex items-center justify-center">
            <Shield size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900">
                Attack Theater: Adversarial BEC Simulation
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200">
                REPLAY
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Deterministic comparison: Naive Agent vs. Warden Bouncer on prompt-injected bank swap
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Sound Toggle */}
          <button
            onClick={toggleSound}
            className="p-2 rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 transition-all cursor-pointer"
            title={soundEnabled ? 'Mute attack sound' : 'Enable quiet UI audio'}
            aria-label={soundEnabled ? 'Mute attack sound' : 'Enable quiet UI audio'}
          >
            {soundEnabled ? <Volume2 size={14} /> : <VolumeX size={14} className="opacity-50" />}
          </button>

          {/* Run Attack Control Button */}
          <button
            onClick={handleRunAttack}
            disabled={isRunning}
            className="nixtio-pill-dark px-4 py-2 text-xs font-bold flex items-center gap-2 cursor-pointer disabled:opacity-50 shadow-sm"
          >
            <Play size={13} className={isRunning ? 'animate-spin' : 'fill-white'} />
            <span>{isRunning ? 'Evaluating C1..C8...' : 'Run Attack Simulation'}</span>
          </button>

          {stamped && (
            <button
              onClick={handleReset}
              className="p-2 rounded-full border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-700 transition-all cursor-pointer"
              title="Reset simulation"
            >
              <RotateCcw size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Adversarial Prompt Context Box */}
      <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5 font-mono text-xs">
        <div className="flex items-center justify-between text-[11px] text-slate-500 font-semibold">
          <span>Adversary Prompt Injection Payload:</span>
          <span>Target Payee: billing-partner@evil.test</span>
        </div>
        <p className="text-slate-800 text-[11px] bg-white p-2.5 rounded-xl border border-slate-200 leading-relaxed font-sans">
          "{scenario.attackerMessage}"
        </p>
      </div>

      {/* C1..C8 Monospace Policy Engine Checklist */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-bold text-slate-700">
          <span>Deterministic Bouncer Engine (C1..C8 Pipeline):</span>
          <span className="font-mono text-[11px] text-slate-400">
            {activeCheckIndex >= 0 ? `Evaluating check ${Math.min(activeCheckIndex + 1, 8)}/8` : 'Awaiting trigger'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 font-mono text-xs">
          {scenario.checks.map((chk, idx) => {
            const isEvaluated = activeCheckIndex >= idx;
            const isCurrent = activeCheckIndex === idx;
            const isPass = chk.status === 'PASS';

            return (
              <div
                key={chk.id}
                className={`p-2.5 rounded-xl border transition-all ${
                  !isEvaluated
                    ? 'bg-white border-slate-200 opacity-40'
                    : isCurrent
                    ? 'bg-blue-50/50 border-blue-300 ring-2 ring-blue-500/20'
                    : isPass
                    ? 'bg-white border-slate-200'
                    : 'bg-slate-900 text-white border-slate-900'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-bold text-[11px] ${!isEvaluated ? 'text-slate-500' : isPass ? 'text-slate-900' : 'text-slate-100'}`}>
                    {chk.id}
                  </span>
                  {isEvaluated && (
                    <span className="text-[10px] font-bold">
                      {isPass ? <Check size={12} className="stroke-[3] text-slate-800" /> : <X size={12} className="stroke-[3] text-white" />}
                    </span>
                  )}
                </div>
                <div className="truncate text-[10px] font-semibold opacity-90">{chk.name}</div>
                <div className="truncate text-[9px] opacity-60 mt-0.5">{chk.rationale}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Side-by-Side Comparison: Naive Agent vs. Warden Protocol */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        {/* Left: Naive Agent (Bouncer OFF) */}
        <div className="p-4 rounded-2xl bg-white border border-slate-200 space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-150 pb-2.5">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-slate-500" />
              <span className="text-xs font-bold tracking-wider uppercase text-slate-800">
                Naive Agent
              </span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200">
              BOUNCER OFF
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <span className="text-slate-400 font-semibold block text-[11px]">Proposed Transaction:</span>
            <div className="font-mono text-[11px] p-2 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
              <span>Remit $45.00 to unverified payee</span>
              <span className="font-bold text-slate-900">$45.00 USD</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
            <div className="font-bold text-slate-900 flex items-center gap-1.5">
              <AlertCircle size={14} className="text-slate-700" />
              <span>Prompt Exploit Successful</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Agent trusted conversational instruction. PayPal Payout dispatched to fraudulent offshore clearing partner.
            </p>
            <div className="pt-1.5 border-t border-slate-200 font-mono text-[11px] font-bold text-slate-900">
              Loss: $45.00 Drained (100% Break-in)
            </div>
          </div>
        </div>

        {/* Right: Warden Protocol (Bouncer ON) */}
        <div className="p-4 rounded-2xl bg-slate-50/70 border-2 border-slate-900 space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-slate-900" />
              <span className="text-xs font-bold tracking-wider uppercase text-slate-900">
                Warden Protected Agent
              </span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-900 text-white">
              BOUNCER ON
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <span className="text-slate-400 font-semibold block text-[11px]">Enforced Mandate Boundary:</span>
            <div className="font-mono text-[11px] p-2 rounded-lg bg-white border border-slate-200 flex justify-between items-center">
              <span className={stamped ? 'line-through text-slate-400' : 'text-slate-800'}>
                Remit $45.00 to unlisted payee
              </span>
              <span className={`font-bold ${stamped ? 'line-through text-slate-400' : 'text-slate-900'}`}>
                $45.00 USD
              </span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-white border border-slate-200 text-xs space-y-1 relative">
            <div className="font-bold text-slate-900 flex items-center gap-1.5">
              <ShieldOff size={14} className="text-slate-900" />
              <span>Deterministic Policy Interception</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Check C3 failed: recipient email is missing from Ed25519 standing allowlist. Settlement rail blocked before payment execution.
            </p>
            <div className="pt-1.5 border-t border-slate-200 font-mono text-[11px] font-bold text-slate-900">
              Loss: $0.00 Stolen (100% Defense)
            </div>

            {/* Verdict Stamp Effect */}
            {stamped && (
              <div
                ref={stampRef}
                className="absolute inset-0 flex items-center justify-center bg-white/90 backdrop-blur-2xs rounded-xl"
              >
                <div className="flex flex-col items-center gap-1">
                  <VerdictBadge verdict="BLOCK" size="lg" />
                  <span className="font-mono text-[9px] uppercase tracking-widest text-slate-400">
                    SETTLEMENT RAIL HALTED
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
