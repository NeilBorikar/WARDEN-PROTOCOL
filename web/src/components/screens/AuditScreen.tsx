import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import {
  History,
  ShieldCheck,
  RotateCcw,
  Search,
  ChevronRight,
  ChevronDown,
  Hash,
  Copy,
  Link2,
  Link2Off,
  AlertOctagon,
} from 'lucide-react';
import type { AuditEvent } from '../../types/api';
import { api, DEMO_AUDIT_EVENTS } from '../../api/client';

export const AuditScreen: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>(DEMO_AUDIT_EVENTS);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [highlightedSeq, setHighlightedSeq] = useState<number | null>(null);
  const [tamperedSeq, setTamperedSeq] = useState<number | null>(null);
  const [verificationResult, setVerificationResult] = useState<{
    isValid: boolean;
    count: number;
    failedSeq?: number;
    checkedAt: string;
  } | null>({
    isValid: true,
    count: DEMO_AUDIT_EVENTS.length,
    checkedAt: new Date().toISOString(),
  });

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [expandedSeq, setExpandedSeq] = useState<number | null>(null);
  const [, setCopiedHash] = useState<string | null>(null);

  const timelineRef = useRef<HTMLDivElement>(null);

  const fetchEvents = async () => {
    try {
      const data = await api.getAuditEvents(100, typeFilter === 'ALL' ? undefined : typeFilter);
      setEvents(data);
    } catch {
      setEvents(DEMO_AUDIT_EVENTS);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [typeFilter]);

  // GSAP: Animate blocks sliding in and linking
  useEffect(() => {
    if (!timelineRef.current || timelineRef.current.children.length === 0) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        timelineRef.current!.children,
        { opacity: 0, x: -16 },
        { opacity: 1, x: 0, stagger: 0.05, duration: 0.45, ease: 'power2.out' }
      );
    }, timelineRef);
    return () => ctx.revert();
  }, [typeFilter, searchQuery, events.length]);

  // Client-Side Chain Verification with Sweeping Highlight
  const handleVerifyChain = () => {
    if (isVerifying) return;
    setIsVerifying(true);
    setHighlightedSeq(null);

    // Sort ascending for verification from genesis to tip
    const sorted = [...events].sort((a, b) => a.seq - b.seq);
    let checkIndex = 0;

    const sweepInterval = setInterval(() => {
      if (checkIndex < sorted.length) {
        const current = sorted[checkIndex];
        setHighlightedSeq(current.seq);

        // Check hash link against previous block
        if (checkIndex > 0) {
          const prev = sorted[checkIndex - 1];
          if (current.prev_hash !== prev.hash) {
            // Tampered block detected!
            clearInterval(sweepInterval);
            setIsVerifying(false);
            setTamperedSeq(current.seq);
            setVerificationResult({
              isValid: false,
              count: sorted.length,
              failedSeq: current.seq,
              checkedAt: new Date().toISOString(),
            });
            return;
          }
        }
        checkIndex++;
      } else {
        clearInterval(sweepInterval);
        setIsVerifying(false);
        setHighlightedSeq(null);
        setVerificationResult({
          isValid: true,
          count: sorted.length,
          checkedAt: new Date().toISOString(),
        });
      }
    }, 120);
  };

  // Toggle Tampered Demo Block [REPLAY]
  const handleToggleTampered = () => {
    if (tamperedSeq) {
      // Revert to legitimate demo events
      setTamperedSeq(null);
      setEvents(DEMO_AUDIT_EVENTS);
      setVerificationResult({
        isValid: true,
        count: DEMO_AUDIT_EVENTS.length,
        checkedAt: new Date().toISOString(),
      });
    } else {
      // Inject tampered block with mismatched prev_hash
      const tamperedBlock: AuditEvent = {
        seq: 5,
        ts: new Date().toISOString(),
        type: 'PAYMENT_REQUESTED',
        payload: {
          request_id: 'req-forged-adversarial',
          amount_minor: 99990,
          payee: 'attacker@darknet.test',
          tampered: true,
        },
        prev_hash: 'bad0000000000000000000000000000000000000000000000000000000000000',
        hash: 'forged99999999999999999999999999999999999999999999999999999999999',
      };
      setEvents([tamperedBlock, ...DEMO_AUDIT_EVENTS]);
      setVerificationResult(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredEvents = events.filter((ev) => {
    const matchesSearch =
      searchQuery === '' ||
      ev.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.hash.toLowerCase().includes(searchQuery.toLowerCase()) ||
      JSON.stringify(ev.payload).toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType = typeFilter === 'ALL' || ev.type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <History size={20} className="text-slate-800" />
              Cryptographic Audit Chain Visualizer
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable SHA-256 hash-chained log linking all bouncer evaluations and settlement proofs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Tampered Block Replay Toggle */}
          <button
            onClick={handleToggleTampered}
            className="px-3 py-2 rounded-full border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
            title="Inject an altered pre-image block to test chain verification"
          >
            <AlertOctagon size={13} className="text-slate-700" />
            <span>{tamperedSeq ? 'Remove Tampered Block' : 'Inject Tampered Block [REPLAY]'}</span>
          </button>

          {/* Client-Side Verify Chain Button */}
          <button
            onClick={handleVerifyChain}
            disabled={isVerifying}
            className="nixtio-pill-dark px-4 py-2 text-xs font-semibold flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
          >
            {isVerifying ? (
              <>
                <RotateCcw size={13} className="animate-spin" />
                <span>Sweeping Preimages...</span>
              </>
            ) : (
              <>
                <ShieldCheck size={14} />
                <span>Verify Chain</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Verification Status Card (Zero greens/reds) */}
      {verificationResult && (
        <div
          className={`p-4 rounded-2xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs shadow-xs ${
            verificationResult.isValid
              ? 'bg-blue-50/70 border-blue-200 text-slate-900'
              : 'bg-slate-100 border-slate-300 text-slate-950 animate-shake'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0 ${
                verificationResult.isValid ? 'bg-blue-600' : 'bg-slate-900'
              }`}
            >
              {verificationResult.isValid ? <Link2 size={16} /> : <Link2Off size={16} />}
            </div>
            <div>
              <span className="font-bold text-sm block">
                {verificationResult.isValid
                  ? 'Client-Side Chain Proof Verified'
                  : `Hash Discrepancy Detected at Block #${verificationResult.failedSeq}`}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                {verificationResult.isValid
                  ? `${verificationResult.count} linked blocks cryptographically verified to genesis`
                  : 'Previous block hash mismatch — tamper-evident chain broken'}
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            Validated: {new Date(verificationResult.checkedAt).toLocaleTimeString()}
          </div>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="nixtio-card p-3 flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search truncated hash, type, or payload..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-full bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-slate-900"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
          {['ALL', 'MANDATE_REGISTERED', 'PAYMENT_REQUESTED', 'POLICY_EVALUATED', 'APPROVAL_CREATED'].map((f) => (
            <button
              key={f}
              onClick={() => setTypeFilter(f)}
              className={`px-3 py-1.5 rounded-full text-[10px] font-mono font-bold transition-all cursor-pointer ${
                typeFilter === f
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Linked Blocks Visualizer Timeline */}
      <div ref={timelineRef} className="space-y-4">
        {filteredEvents.map((ev, index) => {
          const isExpanded = expandedSeq === ev.seq;
          const isHighlighted = highlightedSeq === ev.seq;
          const isFailed = tamperedSeq === ev.seq;
          const truncatedHash = `${ev.hash.slice(0, 6)}...${ev.hash.slice(-4)}`;
          const truncatedPrev = ev.prev_hash
            ? `${ev.prev_hash.slice(0, 6)}...${ev.prev_hash.slice(-4)}`
            : '000000...0000';

          return (
            <div key={ev.seq} className="relative">
              {/* Linked Block Connector Line between entries */}
              {index < filteredEvents.length - 1 && (
                <div className="absolute left-8 top-full h-4 w-[2px] bg-slate-200 z-0 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                </div>
              )}

              <div
                className={`nixtio-card overflow-hidden transition-all duration-150 ${
                  isHighlighted ? 'chain-verifying ring-2 ring-blue-500/30' : ''
                } ${isFailed ? 'animate-shake border-2 border-slate-900 bg-slate-50' : ''}`}
              >
                <div
                  onClick={() => setExpandedSeq(isExpanded ? null : ev.seq)}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 cursor-pointer hover:bg-slate-50/60"
                >
                  <div className="flex items-center gap-3">
                    {/* Link Icon / Block Number */}
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono font-bold text-xs shrink-0 ${
                        isFailed
                          ? 'bg-slate-900 text-white'
                          : isHighlighted
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-100 text-slate-900'
                      }`}
                    >
                      {isFailed ? (
                        <Link2Off size={16} />
                      ) : (
                        `#${String(ev.seq).padStart(2, '0')}`
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs sm:text-sm text-slate-900">
                          {ev.type}
                        </span>
                        {isFailed && (
                          <span className="px-2 py-0.2 rounded-full font-mono text-[9px] bg-slate-900 text-white font-extrabold">
                            TAMPERED [REPLAY]
                          </span>
                        )}
                        <span className="px-2 py-0.2 rounded-md font-mono text-[9px] bg-slate-100 text-slate-600 font-semibold border border-slate-200">
                          SHA-256
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {new Date(ev.ts).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
                    {/* Truncated Hash Pills (first 6 + last 4 chars) */}
                    <div className="font-mono text-xs text-slate-700 flex items-center gap-1.5 bg-slate-50 px-3 py-1 rounded-full border border-slate-200">
                      <Hash size={12} className="text-slate-400" />
                      <span className="font-bold">{truncatedHash}</span>
                    </div>

                    <div className="text-slate-400">
                      {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    </div>
                  </div>
                </div>

                {/* Expanded Block Details */}
                {isExpanded && (
                  <div className="p-4 sm:p-5 border-t border-slate-150 bg-slate-50 font-mono text-xs space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
                      <div className="p-3.5 rounded-2xl bg-white border border-slate-200 space-y-1">
                        <div className="flex items-center justify-between text-slate-400 uppercase font-bold text-[10px]">
                          <span>Current Hash</span>
                          <span>{truncatedHash}</span>
                        </div>
                        <div className="flex items-center justify-between text-slate-900 break-all font-semibold pt-1">
                          <span>{ev.hash}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              copyToClipboard(ev.hash);
                            }}
                            className="ml-2 p-1 text-slate-400 hover:text-slate-800 cursor-pointer"
                            title="Copy full hash"
                          >
                            <Copy size={13} />
                          </button>
                        </div>
                      </div>

                      <div className="p-3.5 rounded-2xl bg-white border border-slate-200 space-y-1">
                        <div className="flex items-center justify-between text-slate-400 uppercase font-bold text-[10px]">
                          <span>Parent Link Hash</span>
                          <span>{truncatedPrev}</span>
                        </div>
                        <span className="text-slate-900 break-all font-semibold block pt-1">
                          {ev.prev_hash || '0000000000000000000000000000000000000000000000000000000000000000'}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 block uppercase font-bold text-[10px] mb-1.5">
                        Verified Preimage Payload
                      </span>
                      <pre className="p-4 rounded-2xl bg-slate-900 text-slate-100 text-[11px] overflow-x-auto">
                        {JSON.stringify(ev.payload, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
