import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import {
  CheckCircle,
  Clock,
  ShieldAlert,
  RotateCcw,
  ShieldCheck,
  Check,
  X,
  UserCheck,
  DollarSign,
  KeyRound,
  Inbox,
  AlertTriangle,
} from 'lucide-react';
import type { ApprovalItem } from '../../types/api';
import { api, DEMO_APPROVALS } from '../../api/client';
import { MoneyDisplay } from '../common/MoneyDisplay';
import { AnimatedCounter } from '../common/AnimatedCounter';

interface ApprovalsScreenProps {
  onApprovalResolved?: () => void;
}

export const ApprovalsScreen: React.FC<ApprovalsScreenProps> = ({ onApprovalResolved }) => {
  const [approvals, setApprovals] = useState<ApprovalItem[]>(DEMO_APPROVALS);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeFilter, setActiveFilter] = useState<'PENDING' | 'RESOLVED' | 'ALL'>('PENDING');
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'deny' | null>(null);
  const [actionNote, setActionNote] = useState<string>('');
  const [resolutionNotice, setResolutionNotice] = useState<{
    msg: string;
    type: 'success' | 'danger';
    txId?: string;
  } | null>(null);

  const listRef = useRef<HTMLDivElement>(null);

  const fetchApprovals = async () => {
    setIsLoading(true);
    try {
      const data = await api.getApprovals();
      setApprovals(data);
    } catch {
      setApprovals(DEMO_APPROVALS);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  // GSAP: Animate cards when list updates (StrictMode safe)
  useEffect(() => {
    if (!listRef.current || listRef.current.children.length === 0) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        listRef.current!.children,
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, stagger: 0.05, duration: 0.4, ease: 'power2.out' }
      );
    }, listRef);
    return () => ctx.revert();
  }, [activeFilter, approvals]);

  const handleOpenModal = (appr: ApprovalItem, type: 'approve' | 'deny') => {
    setSelectedApproval(appr);
    setActionType(type);
    setActionNote(type === 'approve' ? 'Approved by owner via security console' : 'Rejected: unverified expense');
  };

  const handleConfirmAction = async () => {
    if (!selectedApproval || !actionType) return;

    try {
      const outcome = await api.resolveApproval(selectedApproval.approval_id, actionType, actionNote);
      
      setApprovals((prev) =>
        prev.map((item) =>
          item.approval_id === selectedApproval.approval_id
            ? {
                ...item,
                status: actionType === 'approve' ? 'APPROVED' : 'DENIED',
                resolved_at: new Date().toISOString(),
                resolution_reason: actionNote,
              }
            : item
        )
      );

      setResolutionNotice({
        msg:
          actionType === 'approve'
            ? `Successfully authorized payment of $${(selectedApproval.amount_minor / 100).toFixed(2)} to ${selectedApproval.payee_email}. Hard caps re-verified.`
            : `Denied payment request ${selectedApproval.request_id}. Agent spend halted.`,
        type: actionType === 'approve' ? 'success' : 'danger',
        txId: outcome.rail_payment_id || undefined,
      });

      if (onApprovalResolved) {
        onApprovalResolved();
      }
    } catch (err) {
      console.error(err);
      alert('Error updating approval status');
    } finally {
      setSelectedApproval(null);
      setActionType(null);
    }
  };

  const pendingList = approvals.filter((a) => a.status === 'PENDING');
  const resolvedList = approvals.filter((a) => a.status !== 'PENDING');
  const displayedList =
    activeFilter === 'PENDING'
      ? pendingList
      : activeFilter === 'RESOLVED'
      ? resolvedList
      : approvals;

  const totalPendingAmount = pendingList.reduce((acc, curr) => acc + curr.amount_minor, 0);

  return (
    <div className="space-y-6">
      {/* 4 Nixtio KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="nixtio-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Pending Actions
            </span>
            <div className="w-9 h-9 rounded-2xl nixtio-icon-orange flex items-center justify-center">
              <Clock size={16} />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900 font-mono">
              <AnimatedCounter value={pendingList.length} />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Require owner verification
            </p>
          </div>
        </div>

        <div className="nixtio-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Escalated Value
            </span>
            <div className="w-9 h-9 rounded-2xl nixtio-icon-blue flex items-center justify-center">
              <DollarSign size={16} />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900 font-mono">
              <MoneyDisplay amountMinor={totalPendingAmount} />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Awaiting release or rejection
            </p>
          </div>
        </div>

        <div className="nixtio-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Hard Cap Bounded
            </span>
            <div className="w-9 h-9 rounded-2xl nixtio-icon-indigo flex items-center justify-center">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900 font-mono">
              $100 / $500
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Strict per-tx & daily caps
            </p>
          </div>
        </div>

        <div className="nixtio-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Resolved Decisions
            </span>
            <div className="w-9 h-9 rounded-2xl nixtio-icon-teal flex items-center justify-center">
              <UserCheck size={16} />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900 font-mono">
              <AnimatedCounter value={resolvedList.length} />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Cryptographically signed
            </p>
          </div>
        </div>
      </div>

      {/* Resolution Toast Notification (Zero greens / reds) */}
      {resolutionNotice && (
        <div
          className={`p-4 rounded-2xl border flex items-center justify-between gap-3 shadow-md ${
            resolutionNotice.type === 'success'
              ? 'bg-blue-50 border-blue-200 text-blue-900'
              : 'bg-slate-100 border-slate-200 text-slate-900'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {resolutionNotice.type === 'success' ? (
              <CheckCircle size={18} className="text-blue-600 shrink-0" />
            ) : (
              <ShieldAlert size={18} className="text-slate-700 shrink-0" />
            )}
            <div className="text-xs">
              <span className="font-bold">{resolutionNotice.msg}</span>
              {resolutionNotice.txId && (
                <span className="block font-mono text-[11px] mt-0.5 text-slate-500">
                  PayPal Rail Tx: {resolutionNotice.txId}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => setResolutionNotice(null)}
            className="text-xs opacity-60 hover:opacity-100 p-1 cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Filter Tabs & Refresh Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="inline-flex items-center gap-1.5 p-1 rounded-full bg-slate-100 border border-slate-200/80">
          <button
            onClick={() => setActiveFilter('PENDING')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeFilter === 'PENDING'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Pending ({pendingList.length})
          </button>
          <button
            onClick={() => setActiveFilter('RESOLVED')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeFilter === 'RESOLVED'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Resolved ({resolvedList.length})
          </button>
          <button
            onClick={() => setActiveFilter('ALL')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeFilter === 'ALL'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            All ({approvals.length})
          </button>
        </div>

        <button
          onClick={fetchApprovals}
          disabled={isLoading}
          className="nixtio-pill-dark px-4 py-2 text-xs font-semibold flex items-center gap-2 cursor-pointer"
        >
          <RotateCcw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Approvals Cards Grid */}
      <div ref={listRef} className="space-y-3.5">
        {displayedList.length === 0 ? (
          <div className="text-center py-12 rounded-3xl border border-dashed border-slate-200 bg-white/60">
            <Inbox size={32} className="mx-auto text-slate-300 mb-2" />
            <h4 className="text-sm font-bold text-slate-800">
              No Approvals in this View
            </h4>
            <p className="text-xs text-slate-400 mt-1">
              All agent spending requests are verified.
            </p>
          </div>
        ) : (
          displayedList.map((appr) => {
            const isPending = appr.status === 'PENDING';
            const isApproved = appr.status === 'APPROVED';
            const reasonText = appr.reasons?.map((r) => r.message).join(' | ') || 'Approval threshold exceeded';

            return (
              <div
                key={appr.approval_id}
                className="nixtio-card p-5"
              >
                <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                  
                  {/* Left Column: Details */}
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-400">
                        {appr.approval_id}
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="font-mono text-xs text-slate-600">
                        Req: {appr.request_id}
                      </span>
                      {isPending ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          PENDING OWNER REVIEW
                        </span>
                      ) : isApproved ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-100 text-blue-800 border border-blue-200">
                          APPROVED BY OWNER
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-900 text-white">
                          DENIED BY OWNER
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-baseline gap-3">
                      <MoneyDisplay
                        amountMinor={appr.amount_minor}
                        currency={appr.currency}
                        className="text-2xl sm:text-3xl font-black text-slate-900"
                        showCurrency
                      />
                      <span className="text-xs text-slate-400">to</span>
                      <span className="font-mono text-xs sm:text-sm font-bold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-100">
                        {appr.payee_email}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                      <span className="font-semibold text-slate-800">
                        Trigger Rationale:
                      </span>
                      <span className="px-2.5 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-[11px] font-mono text-slate-700">
                        {reasonText}
                      </span>
                      <span className="text-slate-400 text-[11px]">
                        Created {new Date(appr.created_at).toLocaleString()}
                      </span>
                    </div>

                    {appr.resolution_reason && (
                      <p className="text-[11px] text-slate-500 italic bg-slate-50 p-2.5 rounded-xl border border-slate-150">
                        Owner note: "{appr.resolution_reason}"
                      </p>
                    )}
                  </div>

                  {/* Right Column: Actions (Zero Greens / Reds) */}
                  {isPending && (
                    <div className="flex items-center gap-2 shrink-0 w-full lg:w-auto">
                      <button
                        onClick={() => handleOpenModal(appr, 'approve')}
                        className="nixtio-pill-dark px-5 py-2.5 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
                      >
                        <Check size={15} />
                        <span>Authorize & Sign</span>
                      </button>

                      <button
                        onClick={() => handleOpenModal(appr, 'deny')}
                        className="px-4 py-2.5 rounded-full border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all cursor-pointer"
                      >
                        <X size={15} />
                        <span>Reject</span>
                      </button>
                    </div>
                  )}

                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Confirmation & Signing Modal */}
      {selectedApproval && actionType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-md">
          <div className="w-full max-w-lg nixtio-card p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-150">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl flex items-center justify-center text-white bg-slate-900">
                  {actionType === 'approve' ? <KeyRound size={17} /> : <AlertTriangle size={17} />}
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    {actionType === 'approve' ? 'Sign Single-Use Approval Token' : 'Reject Spend Proposal'}
                  </h3>
                  <span className="text-[11px] text-slate-400">Ed25519 Owner Verification</span>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedApproval(null);
                  setActionType(null);
                }}
                className="p-1 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Request ID:</span>
                <span className="font-mono text-slate-800 font-semibold">{selectedApproval.request_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Amount:</span>
                <MoneyDisplay amountMinor={selectedApproval.amount_minor} className="text-sm font-bold text-slate-900" />
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Payee Email:</span>
                <span className="font-mono text-slate-800 font-semibold">{selectedApproval.payee_email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Escalation Trigger:</span>
                <span className="font-mono text-amber-600 font-bold">
                  {selectedApproval.reasons?.map((r) => r.message).join(' | ') || 'Approval threshold exceeded'}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Owner Audit Note:
              </label>
              <input
                type="text"
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
                className="w-full px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50 text-slate-900 text-xs focus:outline-hidden focus:ring-2 focus:ring-slate-900"
                placeholder="Audit explanation note"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-150">
              <button
                onClick={() => {
                  setSelectedApproval(null);
                  setActionType(null);
                }}
                className="px-4 py-2 rounded-full text-xs font-semibold text-slate-500 hover:bg-slate-100 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                className="nixtio-pill-dark px-5 py-2.5 text-xs font-bold cursor-pointer"
              >
                {actionType === 'approve' ? 'Sign & Dispatch to PayPal Rail' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
