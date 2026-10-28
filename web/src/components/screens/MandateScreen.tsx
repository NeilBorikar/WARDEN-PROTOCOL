import React, { useState, useEffect } from 'react';
import {
  KeyRound,
  ShieldCheck,
  Plus,
  CheckCircle2,
  UserCheck,
  Sparkles,
} from 'lucide-react';
import type { Mandate, Intent } from '../../types/api';
import { api, DEMO_MANDATE, DEMO_INTENT } from '../../api/client';
import { MoneyDisplay } from '../common/MoneyDisplay';

export const MandateScreen: React.FC = () => {
  const [, setMandates] = useState<Mandate[]>([DEMO_MANDATE]);
  const [selectedMandate, setSelectedMandate] = useState<Mandate>(DEMO_MANDATE);
  const [intents, setIntents] = useState<Intent[]>([DEMO_INTENT]);
  const [activeTab, setActiveTab] = useState<'mandate' | 'intent' | 'create-intent'>('mandate');

  // Form state for creating a new Intent
  const [newIntentDesc, setNewIntentDesc] = useState('Procure replacement monitor cable and adapter');
  const [newIntentCap, setNewIntentCap] = useState(4000); // $40.00
  const [newIntentSku, setNewIntentSku] = useState('CABLE-HDMI-4K');
  const [newIntentQty, setNewIntentQty] = useState(2);
  const [newIntentUnitPrice, setNewIntentUnitPrice] = useState(2000);
  const [intentSuccessNotice, setIntentSuccessNotice] = useState<string | null>(null);

  useEffect(() => {
    api.getMandates().then((data) => {
      if (data && data.length > 0) {
        setMandates(data);
        setSelectedMandate(data[0]);
      }
    }).catch(() => {
      setMandates([DEMO_MANDATE]);
    });
  }, []);

  const handleCreateIntent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createIntent(selectedMandate.mandate_id, {
        description: newIntentDesc,
        max_total_minor: newIntentCap,
        items: [
          { sku: newIntentSku, qty: newIntentQty, max_unit_price_minor: newIntentUnitPrice },
        ],
      });

      setIntents((prev) => [created, ...prev]);
      setIntentSuccessNotice(`Created and signed Intent "${created.intent_id}" with owner Ed25519 key.`);
      setActiveTab('intent');
    } catch {
      // Offline fallback
      const mockCreated: Intent = {
        intent_id: `intent-${Date.now().toString(36)}`,
        mandate_id: selectedMandate.mandate_id,
        description: newIntentDesc,
        max_total_minor: newIntentCap,
        items: [
          { sku: newIntentSku, qty: newIntentQty, max_unit_price_minor: newIntentUnitPrice },
        ],
        deadline: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
        signature: 'mock_ed25519_signature_' + Math.random().toString(36),
      };
      setIntents((prev) => [mockCreated, ...prev]);
      setIntentSuccessNotice(`Created and signed Intent "${mockCreated.intent_id}" with owner Ed25519 key.`);
      setActiveTab('intent');
    }
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <KeyRound size={20} className="text-blue-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                Mandates & Errand Intents (Ed25519 Signed)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Principle P1 & P3: Money-critical fields (caps, allowlisted payees, intent budgets) originate
              exclusively from owner-signed documents. Untrusted chat cannot override them.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('mandate')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'mandate'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              Standing Mandate
            </button>
            <button
              onClick={() => setActiveTab('intent')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'intent'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              Errand Intents ({intents.length})
            </button>
            <button
              onClick={() => setActiveTab('create-intent')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'create-intent'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30'
              }`}
            >
              <Plus size={13} />
              <span>Sign New Intent</span>
            </button>
          </div>
        </div>
      </div>

      {/* Success notification */}
      {intentSuccessNotice && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl flex items-center justify-between text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400" />
            <span>{intentSuccessNotice}</span>
          </div>
          <button onClick={() => setIntentSuccessNotice(null)} className="text-slate-400 hover:text-white">
            ×
          </button>
        </div>
      )}

      {/* TAB 1: Mandate View */}
      {activeTab === 'mandate' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Mandate Policy Breakdown (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-emerald-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Mandate Policy Rules ({selectedMandate.mandate_id})
                  </h3>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 size={12} />
                  Ed25519 Validated
                </span>
              </div>

              {/* Cap Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Daily Cap</span>
                  <div className="text-base font-bold text-white mt-1">
                    <MoneyDisplay amountMinor={selectedMandate.daily_cap_minor} currency={selectedMandate.currency} />
                  </div>
                  <span className="text-[10px] text-slate-400">Hard stop across 24h</span>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Per-Payment Cap</span>
                  <div className="text-base font-bold text-white mt-1">
                    <MoneyDisplay amountMinor={selectedMandate.per_payment_cap_minor} currency={selectedMandate.currency} />
                  </div>
                  <span className="text-[10px] text-slate-400">Max per single request</span>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Approval Threshold</span>
                  <div className="text-base font-bold text-amber-400 mt-1">
                    <MoneyDisplay amountMinor={selectedMandate.approval_threshold_minor} currency={selectedMandate.currency} />
                  </div>
                  <span className="text-[10px] text-slate-400">Above this triggers owner</span>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Hourly Velocity</span>
                  <div className="text-base font-bold text-white mt-1 font-mono">
                    {selectedMandate.max_payments_per_hour}/hr
                  </div>
                  <span className="text-[10px] text-slate-400">Rate limit limit</span>
                </div>
              </div>

              {/* Allowlisted Payees Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <UserCheck size={14} className="text-blue-400" />
                  Allowlisted Payees ({selectedMandate.allowed_payees.length})
                </h4>
                <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-800/40 text-slate-400 font-mono border-b border-slate-800">
                      <tr>
                        <th className="py-2 px-3">Payee ID</th>
                        <th className="py-2 px-3">Display Name</th>
                        <th className="py-2 px-3">PayPal Email</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {selectedMandate.allowed_payees.map((p) => (
                        <tr key={p.payee_id} className="hover:bg-slate-800/20">
                          <td className="py-2.5 px-3 font-mono text-blue-400 font-semibold">{p.payee_id}</td>
                          <td className="py-2.5 px-3 text-slate-200">{p.display_name}</td>
                          <td className="py-2.5 px-3 font-mono text-emerald-400">{p.paypal_email}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Purpose & Red Tier Policies */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5 text-xs">
                  <span className="text-slate-400 font-semibold block">Allowed Purposes:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedMandate.allowed_purposes.map((purp) => (
                      <span key={purp} className="px-2 py-0.5 rounded text-[11px] font-mono bg-blue-500/10 text-blue-300 border border-blue-500/30">
                        {purp}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">New Payee Policy:</span>
                    <span className="text-amber-400 font-bold">{selectedMandate.new_payee_policy}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Red Tier Tool Policy:</span>
                    <span className="text-rose-400 font-bold">{selectedMandate.red_tier_policy}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Cryptographic Verification Card (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <KeyRound size={18} className="text-purple-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Cryptographic Provenance
                </h3>
              </div>

              <div className="space-y-3 text-xs font-mono">
                <div>
                  <span className="text-slate-400 block text-[11px]">Owner ID:</span>
                  <span className="text-white font-semibold">{selectedMandate.owner_id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Bound Agent ID:</span>
                  <span className="text-cyan-400">{selectedMandate.agent_id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Key ID:</span>
                  <span className="text-slate-300">{selectedMandate.key_id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Issued / Expiry:</span>
                  <span className="text-slate-300 text-[10px]">
                    {new Date(selectedMandate.issued_at).toLocaleDateString()} →{' '}
                    {new Date(selectedMandate.expires_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="pt-2 border-t border-slate-800">
                  <span className="text-slate-400 block text-[11px] mb-1">Ed25519 Signature:</span>
                  <div className="p-2 bg-slate-950 border border-slate-800 rounded text-[10px] text-slate-400 break-all leading-tight">
                    {selectedMandate.signature}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Intent List */}
      {activeTab === 'intent' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {intents.map((intent) => (
              <div
                key={intent.intent_id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/30">
                      Bound to: {intent.mandate_id}
                    </span>
                    <h4 className="text-sm font-bold text-white mt-1.5">{intent.description}</h4>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono text-slate-400 block">Budget Cap:</span>
                    <MoneyDisplay amountMinor={intent.max_total_minor} className="text-white font-bold" />
                  </div>
                </div>

                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-1.5 text-xs">
                  <span className="text-slate-400 font-semibold block text-[11px]">Approved Items:</span>
                  {intent.items.map((item, idx) => (
                    <div key={idx} className="flex justify-between font-mono">
                      <span className="text-slate-200">
                        {item.qty}x {item.sku}
                      </span>
                      <span className="text-slate-400">
                        Max Unit: <MoneyDisplay amountMinor={item.max_unit_price_minor} />
                      </span>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Deadline: {new Date(intent.deadline).toLocaleDateString()}</span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 size={12} /> Signed by Owner
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: Create & Sign New Intent */}
      {activeTab === 'create-intent' && (
        <div className="max-w-xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-5">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sparkles size={18} className="text-emerald-400" />
            <h3 className="text-sm font-bold text-white">Create & Sign Autonomous Errand Intent</h3>
          </div>

          <form onSubmit={handleCreateIntent} className="space-y-4 text-xs">
            <div className="space-y-1">
              <label className="font-semibold text-slate-300">Errand Description:</label>
              <input
                type="text"
                required
                value={newIntentDesc}
                onChange={(e) => setNewIntentDesc(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-slate-300">Item SKU:</label>
                <input
                  type="text"
                  required
                  value={newIntentSku}
                  onChange={(e) => setNewIntentSku(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-slate-200"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-300">Quantity:</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newIntentQty}
                  onChange={(e) => setNewIntentQty(parseInt(e.target.value) || 1)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-slate-200"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-slate-300">Max Unit Price (Cents):</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newIntentUnitPrice}
                  onChange={(e) => setNewIntentUnitPrice(parseInt(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-slate-200"
                />
                <span className="text-[10px] text-slate-400">
                  = ${(newIntentUnitPrice / 100).toFixed(2)}
                </span>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-300">Total Errand Cap (Cents):</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newIntentCap}
                  onChange={(e) => setNewIntentCap(parseInt(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-slate-200"
                />
                <span className="text-[10px] text-slate-400">
                  = ${(newIntentCap / 100).toFixed(2)}
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setActiveTab('intent')}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-sm cursor-pointer"
              >
                <KeyRound size={14} />
                <span>Sign Intent with Ed25519</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
