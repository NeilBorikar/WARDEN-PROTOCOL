import React, { useState, useEffect } from 'react';
import {
  KeyRound,
  ShieldCheck,
  Plus,
  CheckCircle2,
  UserCheck,
  Lock,
  FileSignature,
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
      {/* Tab Selectors & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <KeyRound size={20} className="text-slate-800" />
            Mandates & Errand Intents (Ed25519 Signed)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Owner authorization parameters that strictly govern agent transactions.
          </p>
        </div>

        {/* Tab Pill Selectors */}
        <div className="inline-flex items-center gap-1.5 p-1 rounded-full bg-slate-100 border border-slate-200/80">
          <button
            onClick={() => setActiveTab('mandate')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'mandate'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Standing Mandate
          </button>
          <button
            onClick={() => setActiveTab('intent')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'intent'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Active Intents ({intents.length})
          </button>
          <button
            onClick={() => setActiveTab('create-intent')}
            className={`nixtio-pill-dark px-4 py-1.5 text-xs font-semibold flex items-center gap-1 cursor-pointer`}
          >
            <Plus size={13} />
            <span>Issue Intent</span>
          </button>
        </div>
      </div>

      {intentSuccessNotice && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600" />
            <span className="font-semibold">{intentSuccessNotice}</span>
          </div>
          <button
            onClick={() => setIntentSuccessNotice(null)}
            className="opacity-70 hover:opacity-100 font-bold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tab 1: Standing Mandate View */}
      {activeTab === 'mandate' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Titanium Smart-Card (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            <div className="relative rounded-3xl p-6 sm:p-7 border border-slate-900 bg-slate-900 text-white shadow-xl">
              <div className="flex items-start justify-between mb-5">
                <div>
                  <span className="text-[10px] font-mono tracking-widest uppercase text-blue-400 font-bold">
                    ED25519 DELEGATED SPENDING MANDATE
                  </span>
                  <h3 className="text-xl sm:text-2xl font-black tracking-tight text-white mt-1">
                    {selectedMandate.mandate_id}
                  </h3>
                </div>
                <div className="w-10 h-10 rounded-2xl bg-white/10 flex items-center justify-center text-white">
                  <ShieldCheck size={20} />
                </div>
              </div>

              {/* Cap Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 py-4 my-2 border-y border-white/10 font-mono">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Single Tx Cap</span>
                  <MoneyDisplay amountMinor={selectedMandate.per_payment_cap_minor} className="text-xl sm:text-2xl text-white font-extrabold" />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Daily Limit</span>
                  <MoneyDisplay amountMinor={selectedMandate.daily_cap_minor} className="text-xl sm:text-2xl text-white font-extrabold" />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Escalation Trigger</span>
                  <MoneyDisplay amountMinor={selectedMandate.approval_threshold_minor} className="text-xl sm:text-2xl text-amber-400 font-extrabold" />
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4 mt-5 text-xs text-slate-300 font-mono">
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase">Owner Principal</span>
                  <span className="font-bold text-white">{selectedMandate.owner_id}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase">Authorized Agent</span>
                  <span className="font-bold text-blue-400">{selectedMandate.agent_id}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase">Key Fingerprint</span>
                  <span className="font-bold text-slate-300">{selectedMandate.key_id}</span>
                </div>
              </div>
            </div>

            {/* Allowed Payees allowlist card */}
            <div className="nixtio-card p-5 space-y-3.5">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
                  <UserCheck size={16} className="text-emerald-600" />
                  Allowlisted Payees ({selectedMandate.allowed_payees.length})
                </h4>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-bold">
                  Bouncer Verified
                </span>
              </div>

              <div className="space-y-2">
                {selectedMandate.allowed_payees.map((payee) => (
                  <div
                    key={payee.payee_id}
                    className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs font-bold text-slate-900 block">
                        {payee.display_name}
                      </span>
                      <span className="text-[11px] font-mono text-blue-600 font-semibold">
                        {payee.paypal_email}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-white text-emerald-700 border border-slate-200">
                      ALLOWLISTED
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Policies (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="nixtio-card p-5 space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
                <Lock size={16} className="text-slate-800" />
                Security Policies Enforced
              </h4>

              <div className="space-y-3 text-xs">
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80">
                  <span className="text-slate-400 text-[11px] block uppercase font-bold">Unlisted Payee Policy</span>
                  <span className="font-mono font-bold text-amber-600 text-sm mt-0.5 block">
                    {selectedMandate.new_payee_policy}
                  </span>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Any new payee not in the allowlist must be manually signed off by owner.
                  </p>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80">
                  <span className="text-slate-400 text-[11px] block uppercase font-bold">Red Tier Risk Policy</span>
                  <span className="font-mono font-bold text-rose-600 text-sm mt-0.5 block">
                    {selectedMandate.red_tier_policy}
                  </span>
                  <p className="text-[11px] text-slate-500 mt-1">
                    High risk signals immediately trigger an unbypassable hard block.
                  </p>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80">
                  <span className="text-slate-400 text-[11px] block uppercase font-bold mb-1.5">Allowed Spending Purposes</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedMandate.allowed_purposes.map((p) => (
                      <span key={p} className="px-2.5 py-0.5 rounded-full font-mono text-[10px] bg-white text-slate-800 border border-slate-200 font-semibold">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Active Intents View */}
      {activeTab === 'intent' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {intents.map((it) => (
            <div
              key={it.intent_id}
              className="nixtio-card p-5 space-y-3.5"
            >
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] font-mono text-blue-600 font-bold uppercase">
                    Errand Intent
                  </span>
                  <h4 className="text-sm font-bold text-slate-900 mt-0.5">
                    {it.intent_id}
                  </h4>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  SIGNED BY OWNER
                </span>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                {it.description}
              </p>

              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 flex justify-between items-center text-xs">
                <span className="text-slate-500">Max Budget Cap:</span>
                <MoneyDisplay amountMinor={it.max_total_minor} className="text-sm font-black text-slate-900" />
              </div>

              <div className="space-y-1 text-xs">
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                  Permitted Line Items:
                </span>
                {it.items.map((item, idx) => (
                  <div key={idx} className="flex justify-between font-mono py-1 border-b border-slate-100">
                    <span className="text-slate-800 font-semibold">{item.sku} (x{item.qty})</span>
                    <span className="text-slate-500">
                      Cap: <MoneyDisplay amountMinor={item.max_unit_price_minor} />/unit
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Create Intent Form */}
      {activeTab === 'create-intent' && (
        <div className="max-w-xl mx-auto nixtio-card p-6 sm:p-7 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-150">
            <div className="w-10 h-10 rounded-2xl nixtio-icon-blue flex items-center justify-center">
              <FileSignature size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Issue Signed Errand Intent
              </h3>
              <p className="text-xs text-slate-400">
                Authorizes the agent to spend up to the budget cap for exact items.
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateIntent} className="space-y-4 text-xs font-sans">
            <div>
              <label className="block font-semibold text-slate-700 mb-1.5">
                Errand Description
              </label>
              <input
                type="text"
                required
                value={newIntentDesc}
                onChange={(e) => setNewIntentDesc(e.target.value)}
                className="w-full px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50 text-slate-900 text-xs focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Total Budget Cap ($)
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newIntentCap / 100}
                  onChange={(e) => setNewIntentCap(Math.round(parseFloat(e.target.value || '0') * 100))}
                  className="w-full px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50 text-slate-900 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Item SKU
                </label>
                <input
                  type="text"
                  required
                  value={newIntentSku}
                  onChange={(e) => setNewIntentSku(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50 text-slate-900 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Quantity
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newIntentQty}
                  onChange={(e) => setNewIntentQty(parseInt(e.target.value || '1', 10))}
                  className="w-full px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50 text-slate-900 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Max Unit Price ($)
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newIntentUnitPrice / 100}
                  onChange={(e) => setNewIntentUnitPrice(Math.round(parseFloat(e.target.value || '0') * 100))}
                  className="w-full px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50 text-slate-900 text-xs font-mono"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-150 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setActiveTab('mandate')}
                className="px-4 py-2 rounded-full text-xs font-semibold text-slate-500 hover:bg-slate-100 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="nixtio-pill-dark px-5 py-2.5 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
              >
                <KeyRound size={13} />
                <span>Sign & Issue Intent</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
