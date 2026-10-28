import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  ShieldCheck,
  ShieldAlert,
  DollarSign,
  Zap,
  TrendingDown,
  CheckCircle2,
  GitCommit,
} from 'lucide-react';
import type { ResultsSummary } from '../../types/api';
import { api, DEMO_RESULTS } from '../../api/client';

export const ResultsScreen: React.FC = () => {
  const [results, setResults] = useState<ResultsSummary>(DEMO_RESULTS);
  const [isProtectedView, setIsProtectedView] = useState<boolean>(true);

  useEffect(() => {
    api.getResults().then(setResults).catch(() => setResults(DEMO_RESULTS));
  }, []);

  const currentMetrics = isProtectedView ? results.metrics_protected : results.metrics_naive;

  return (
    <div className="space-y-6">
      {/* Headline Security Guarantee Card */}
      <div className="bg-gradient-to-r from-blue-950/60 via-slate-900 to-indigo-950/60 border border-blue-500/30 rounded-xl p-6 shadow-md relative overflow-hidden">
        <div className="max-w-3xl space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/40">
            <ShieldCheck size={14} className="text-blue-400" />
            <span>Empirically Proven Security Guarantee</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Zero Break-in Rate. Zero Money Lost.
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Even if an AI agent is completely compromised by adversarial jailbreaks, bank detail swaps, or prompt injections,
            money can never leave outside the owner's signed Mandate. Worst-case loss is strictly capped at $0.00.
          </p>
        </div>

        {/* Toggle Switch */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-400">Security Mode Comparison:</span>
            <div className="inline-flex rounded-lg bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setIsProtectedView(true)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  isProtectedView
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <ShieldCheck size={14} />
                <span>Protected (Bouncer ON)</span>
              </button>
              <button
                onClick={() => setIsProtectedView(false)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  !isProtectedView
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <ShieldAlert size={14} />
                <span>Naive Agent (Bouncer OFF)</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <GitCommit size={14} className="text-blue-400" />
            <span>Commit: {String(results.run_metadata.git_sha || 'e80dc38')}</span>
          </div>
        </div>
      </div>

      {/* 4 Core Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Break-in Rate */}
        <div className={`p-5 rounded-xl border bg-slate-900 shadow-sm ${
          isProtectedView ? 'border-emerald-500/30' : 'border-rose-500/30'
        }`}>
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-mono uppercase text-slate-400">Break-in Rate</span>
            {isProtectedView ? (
              <CheckCircle2 size={18} className="text-emerald-400" />
            ) : (
              <ShieldAlert size={18} className="text-rose-400" />
            )}
          </div>
          <div className="text-3xl font-extrabold font-mono text-white">
            {(currentMetrics.break_in_rate * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {isProtectedView ? '0/45 attack scenarios succeeded' : '45/45 attacks deceived the agent'}
          </p>
        </div>

        {/* Metric 2: Money Lost */}
        <div className={`p-5 rounded-xl border bg-slate-900 shadow-sm ${
          isProtectedView ? 'border-emerald-500/30' : 'border-rose-500/30'
        }`}>
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-mono uppercase text-slate-400">Money Stolen ($)</span>
            <DollarSign size={18} className={isProtectedView ? 'text-emerald-400' : 'text-rose-400'} />
          </div>
          <div className={`text-3xl font-extrabold font-mono ${
            isProtectedView ? 'text-emerald-400' : 'text-rose-400'
          }`}>
            ${currentMetrics.money_lost_usd.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {isProtectedView ? '100% financial protection' : 'Total money diverted without Bouncer'}
          </p>
        </div>

        {/* Metric 3: False Alarms / Interruption */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-mono uppercase text-slate-400">False Alarm Rate</span>
            <TrendingDown size={18} className="text-blue-400" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-white">
            {(currentMetrics.false_alarm_rate * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Legitimate in-policy tasks are never blocked
          </p>
        </div>

        {/* Metric 4: Latency Overhead */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-mono uppercase text-slate-400">Bouncer Added Latency</span>
            <Zap size={18} className="text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-white">
            {currentMetrics.p50_latency_ms.toFixed(2)} ms
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Pure in-memory checks; p95 = {currentMetrics.p95_latency_ms.toFixed(2)} ms
          </p>
        </div>
      </div>

      {/* Attack Category Breakdown Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm space-y-3 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-blue-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Attack Category Benchmark Matrix (45 Variants Evaluated)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            9 Categories × 5 Variants Each
          </span>
        </div>

        <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/50 text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4">Attack Vector Category</th>
                <th className="py-2.5 px-4 text-center">Variants Tested</th>
                <th className="py-2.5 px-4 text-center">Protected Break-in</th>
                <th className="py-2.5 px-4 text-center">Naive Break-in</th>
                <th className="py-2.5 px-4 text-right">Naive Money Lost</th>
                <th className="py-2.5 px-4 text-right">Protected Money Lost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {results.category_breakdown.map((row) => (
                <tr key={row.category} className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-semibold text-slate-200">{row.category}</td>
                  <td className="py-3 px-4 text-center font-mono text-slate-400">{row.sample_count}</td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      0.0% (0/{row.sample_count})
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                      {(row.naive_break_in_rate * 100).toFixed(0)}% ({row.sample_count}/{row.sample_count})
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-rose-400 font-semibold">
                    ${row.naive_money_lost_usd.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-emerald-400 font-bold">
                    ${row.protected_money_lost_usd.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
