import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  Activity,
  CheckCircle,
  FileCode2,
  History,
  BarChart3,
  Swords,
  Play,
  ShieldCheck,
  ToggleLeft,
  X,
} from 'lucide-react';
import type { ScreenId } from './Header';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (screen: ScreenId) => void;
  onRunAttack?: () => void;
  onVerifyChain?: () => void;
  onToggleBouncerView?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onRunAttack,
  onVerifyChain,
  onToggleBouncerView,
}) => {
  const [query, setQuery] = useState<string>('');
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const actions = [
    {
      id: 'live-run',
      title: 'Navigate to Live Run Console',
      shortcut: 'G L',
      category: 'Navigation',
      icon: Activity,
      perform: () => onNavigate('live-run'),
    },
    {
      id: 'approvals',
      title: 'Review Pending Owner Approvals',
      shortcut: 'G A',
      category: 'Navigation',
      icon: CheckCircle,
      perform: () => onNavigate('approvals'),
    },
    {
      id: 'mandates',
      title: 'Inspect Standing Ed25519 Mandates',
      shortcut: 'G M',
      category: 'Navigation',
      icon: FileCode2,
      perform: () => onNavigate('mandates'),
    },
    {
      id: 'audit',
      title: 'Open Audit Chain Visualizer',
      shortcut: 'G C',
      category: 'Navigation',
      icon: History,
      perform: () => onNavigate('audit'),
    },
    {
      id: 'results',
      title: 'View 45-Scenario Benchmark Results',
      shortcut: 'G B',
      category: 'Navigation',
      icon: BarChart3,
      perform: () => onNavigate('results'),
    },
    {
      id: 'arena',
      title: 'Open Adversarial Arena Terminal',
      shortcut: 'G X',
      category: 'Navigation',
      icon: Swords,
      perform: () => onNavigate('arena'),
    },
    {
      id: 'run-attack',
      title: 'Execute BEC Attack Simulation [REPLAY]',
      shortcut: 'R A',
      category: 'Actions',
      icon: Play,
      perform: () => {
        onNavigate('live-run');
        if (onRunAttack) onRunAttack();
      },
    },
    {
      id: 'verify-chain',
      title: 'Verify SHA-256 Audit Chain Preimages',
      shortcut: 'V C',
      category: 'Actions',
      icon: ShieldCheck,
      perform: () => {
        onNavigate('audit');
        if (onVerifyChain) onVerifyChain();
      },
    },
    {
      id: 'toggle-bouncer',
      title: 'Toggle Bouncer ON / OFF Comparison',
      shortcut: 'T B',
      category: 'Actions',
      icon: ToggleLeft,
      perform: () => {
        onNavigate('results');
        if (onToggleBouncerView) onToggleBouncerView();
      },
    },
  ];

  const filtered = actions.filter((act) =>
    act.title.toLowerCase().includes(query.toLowerCase()) ||
    act.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % (filtered.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].perform();
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filtered, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden animate-chip-pop"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-5 py-3.5 border-b border-slate-150">
          <Search size={16} className="text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or jump to screen..."
            className="w-full text-sm font-medium text-slate-900 bg-transparent placeholder:text-slate-400 focus:outline-hidden"
          />
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Action Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400 font-mono">
              No commands found for "{query}"
            </div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;

              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.perform();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-xs cursor-pointer transition-all ${
                    isSelected ? 'bg-slate-100 text-slate-900' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      <Icon size={14} />
                    </div>
                    <span className="font-semibold">{item.title}</span>
                  </div>

                  <span className="font-mono text-[10px] text-slate-400 uppercase tracking-widest bg-white px-2 py-0.5 rounded-md border border-slate-200">
                    {item.shortcut}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Keyboard Hints Footer */}
        <div className="flex items-center justify-between px-5 py-2.5 bg-slate-50 border-t border-slate-150 text-[10px] font-mono text-slate-400">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>Esc Close</span>
          </div>
          <span>Warden Console v0.1.0</span>
        </div>
      </div>
    </div>
  );
};
