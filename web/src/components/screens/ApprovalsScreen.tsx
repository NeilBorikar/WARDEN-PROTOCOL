import React, { useState, useEffect } from 'react';
import {
  CheckCircle,
  Clock,
  ShieldAlert,
  RotateCcw,
  ShieldCheck,
  Check,
  X,
} from 'lucide-react';
import type { ApprovalItem } from '../../types/api';
import { api, DEMO_APPROVALS } from '../../api/client';
import { MoneyDisplay } from '../common/MoneyDisplay';
import { VerdictBadge } from '../common/VerdictBadge';

interface ApprovalsScreenProps {
  onApprovalResolved?: () => void;
}

export const ApprovalsScreen: React.FC<ApprovalsScreenProps> = ({ onApprovalResolved }) => {
  const [approvals, setApprovals] = useState<ApprovalItem[]>(DEMO_APPROVALS);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'deny' | null>(null);
  const [actionNote, setActionNote] = useState<string>('');
  const [resolutionNotice, setResolutionNotice] = useState<{
    msg: string;
    type: 'success' | 'danger';
    txId?: string;
  } | null>(null);

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

  const handleOpenModal = (appr: ApprovalItem, type: 'approve' | 'deny') => {
    setSelectedApproval(appr);
    setActionType(type);
    setActionNote(type === 'approve' ? 'Approved by owner via security console' : 'Rejected: unverified expense');
  };

  const handleConfirmAction = async () => {
    if (!selectedApproval || !actionType) return;

    try {
      const outcome = await api.resolveApproval(selectedApproval.approval_id, actionType, actionNote);
      
      // Update local state
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

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-amber-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">
              Owner Spending Approvals
            </h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
              {pendingList.length} Pending
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Under Principle P4 & P5, any spend exceeding threshold caps or directed to new payees triggers
            an owner-bound approval request with a 15-minute single-use TTL. Owners cannot approve a BLOCK.
          </p>
        </div>

        <button
          onClick={fetchApprovals}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors cursor-pointer shrink-0"
        >
          <RotateCcw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Resolution Toast Notice */}
      {resolutionNotice && (
        <div
          role="status"
          className={`p-4 rounded-xl border flex items-start justify-between gap-3 ${
            resolutionNotice.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
              : 'bg-rose-950/40 border-rose-800/60 text-rose-300'
          }`}
        >
          <div className="flex items-start gap-2.5">
            {resolutionNotice.type === 'success' ? (
              <CheckCircle size={18} className="text-emerald-400 mt-0.5 shrink-0" />
            ) : (
              <ShieldAlert size={18} className="text-rose-400 mt-0.5 shrink-0" />
            )}
            <div>
              <p className="text-xs font-semibold">{resolutionNotice.msg}</p>
              {resolutionNotice.txId && (
                <p className="text-[11px] font-mono mt-0.5 text-emerald-400">
                  PayPal Transaction Reference: {resolutionNotice.txId}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => setResolutionNotice(null)}
            className="text-slate-400 hover:text-white text-xs cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Pending Approvals Grid */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Clock size={14} className="text-amber-400" />
          Pending Approvals Awaiting Owner Signature
        </h3>

        {pendingList.length === 0 ? (
          <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl">
            <CheckCircle size={36} className="text-emerald-500 mx-auto mb-2 opacity-80" />
            <h4 className="text-sm font-semibold text-slate-200">No Pending Approvals</h4>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              All agent spending requests are either completed or blocked by standing Mandate rules.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pendingList.map((appr) => {
              const expiresMin = Math.max(
                0,
                Math.round((new Date(appr.expires_at).getTime() - Date.now()) / (60 * 1000))
              );

              return (
                <div
                  key={appr.approval_id}
                  className="bg-slate-900 border border-amber-500/30 rounded-xl p-5 shadow-sm space-y-4 relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 right-0 h-1 bg-amber-500/80" />

                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <VerdictBadge verdict="ASK_OWNER" size="sm" />
                        <span className="text-[11px] font-mono text-slate-400">
                          TTL: {expiresMin}m remaining
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-white mt-1">
                        <MoneyDisplay amountMinor={appr.amount_minor} currency={appr.currency} showCurrency />
                      </h4>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] font-mono text-slate-400 block">ID: {appr.approval_id}</span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(appr.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Payee Email:</span>
                      <span className="font-mono text-slate-200 font-semibold truncate max-w-[200px]" title={appr.payee_email}>
                        {appr.payee_email}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Purpose:</span>
                      <span className="font-mono text-slate-300">{appr.purpose}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Memo:</span>
                      <span className="text-slate-300 italic truncate max-w-[220px]" title={appr.memo}>
                        "{appr.memo}"
                      </span>
                    </div>
                    <div className="pt-2 border-t border-slate-900 text-[10px] font-mono text-slate-400 truncate">
                      Request Hash: {appr.request_hash}
                    </div>
                  </div>

                  {/* Plain English Reasons */}
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-semibold text-amber-400 block">
                      Escalation Reason:
                    </span>
                    {appr.reasons.map((r, i) => (
                      <p key={i} className="text-xs text-slate-300 bg-amber-950/20 border border-amber-900/30 p-2 rounded leading-relaxed">
                        • {r.message}
                      </p>
                    ))}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                    <button
                      onClick={() => handleOpenModal(appr, 'approve')}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                    >
                      <Check size={14} />
                      <span>Approve Spend</span>
                    </button>
                    <button
                      onClick={() => handleOpenModal(appr, 'deny')}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-300 text-xs font-semibold transition-colors cursor-pointer"
                    >
                      <X size={14} />
                      <span>Deny Spend</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Resolved History */}
      {resolvedList.length > 0 && (
        <div className="space-y-3 pt-6 border-t border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Resolved Approvals History
          </h3>
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/50 text-slate-400 font-mono border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Amount</th>
                    <th className="py-2.5 px-4">Payee</th>
                    <th className="py-2.5 px-4">Resolution Note</th>
                    <th className="py-2.5 px-4">Resolved At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {resolvedList.map((item) => (
                    <tr key={item.approval_id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            item.status === 'APPROVED'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-white">
                        <MoneyDisplay amountMinor={item.amount_minor} currency={item.currency} />
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">{item.payee_email}</td>
                      <td className="py-3 px-4 text-slate-400 max-w-xs truncate">{item.resolution_reason || '—'}</td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {item.resolved_at ? new Date(item.resolved_at).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {selectedApproval && actionType && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                  actionType === 'approve'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                }`}
              >
                {actionType === 'approve' ? <Check size={20} /> : <X size={20} />}
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {actionType === 'approve' ? 'Authorize Payment' : 'Reject Spending Request'}
                </h3>
                <p className="text-xs text-slate-400">
                  {actionType === 'approve'
                    ? 'Hard caps will be re-evaluated deterministically before money moves.'
                    : 'Transaction will be irrevocably terminated.'}
                </p>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Amount:</span>
                <span className="text-white font-bold">
                  <MoneyDisplay amountMinor={selectedApproval.amount_minor} currency={selectedApproval.currency} />
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Payee:</span>
                <span className="text-slate-200">{selectedApproval.payee_email}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                {actionType === 'approve' ? 'Approval Note (Recorded in Audit Chain):' : 'Reason for Denial:'}
              </label>
              <input
                type="text"
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setSelectedApproval(null);
                  setActionType(null);
                }}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                className={`px-4 py-2 rounded-lg text-white text-xs font-semibold shadow-sm cursor-pointer ${
                  actionType === 'approve'
                    ? 'bg-emerald-600 hover:bg-emerald-500'
                    : 'bg-rose-600 hover:bg-rose-500'
                }`}
              >
                Confirm {actionType === 'approve' ? 'Approval' : 'Denial'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
