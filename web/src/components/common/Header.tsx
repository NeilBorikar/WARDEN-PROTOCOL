import React from 'react';
import {
  Shield,
  Activity,
  CheckCircle,
  FileCode2,
  History,
  BarChart3,
  Swords,
  Moon,
  Sun,
  Flame,
} from 'lucide-react';

export type ScreenId = 'live-run' | 'approvals' | 'mandates' | 'audit' | 'results' | 'arena';

interface HeaderProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
  pendingApprovalsCount: number;
  isDarkMode: boolean;
  onToggleTheme: () => void;
  isDemoMode: boolean;
  onToggleDemoMode: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentScreen,
  onSelectScreen,
  pendingApprovalsCount,
  isDarkMode,
  onToggleTheme,
  isDemoMode,
  onToggleDemoMode,
}) => {
  const navItems: Array<{ id: ScreenId; label: string; icon: React.ComponentType<{ size?: number; className?: string }>; badge?: number }> = [
    { id: 'live-run', label: 'Live Run', icon: Activity },
    { id: 'approvals', label: 'Approvals', icon: CheckCircle, badge: pendingApprovalsCount },
    { id: 'mandates', label: 'Mandate & Intent', icon: FileCode2 },
    { id: 'audit', label: 'Audit Chain', icon: History },
    { id: 'results', label: 'Benchmark Results', icon: BarChart3 },
    { id: 'arena', label: 'Break the Agent', icon: Swords },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 text-slate-100 px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Brand & Security Status */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 shadow-sm shadow-blue-500/10">
              <Shield size={20} className="stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold tracking-tight text-base text-white">WARDEN PROTOCOL</span>
                <span className="px-1.5 py-0.2 bg-blue-500/10 border border-blue-500/30 text-blue-400 text-[10px] font-mono rounded font-medium">
                  v0.1.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-none">
                Autonomous PayPal Agent Safety Layer
              </p>
            </div>
          </div>

          {/* Status Badges */}
          <div className="hidden sm:flex items-center gap-2 ml-4">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Bouncer: Fail-Closed
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              PayPal Payouts Sandbox
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav aria-label="Main Navigation" className="flex items-center gap-1 overflow-x-auto w-full md:w-auto py-1 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentScreen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectScreen(item.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Icon size={14} className={isActive ? 'text-white' : 'text-slate-400'} />
                <span>{item.label}</span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                    isActive ? 'bg-white text-blue-700' : 'bg-amber-500 text-slate-950 animate-pulse'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Global Controls */}
        <div className="hidden lg:flex items-center gap-2.5">
          <button
            onClick={onToggleDemoMode}
            title={isDemoMode ? 'Cassette Replay Mode Active' : 'Live API Backend Active'}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono border transition-colors cursor-pointer ${
              isDemoMode
                ? 'bg-purple-500/10 border-purple-500/30 text-purple-300'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white'
            }`}
          >
            <Flame size={13} className={isDemoMode ? 'text-purple-400' : 'text-slate-400'} />
            <span>{isDemoMode ? 'Cassette Replay' : 'Live API'}</span>
          </button>

          <button
            onClick={onToggleTheme}
            aria-label="Toggle visual theme"
            className="p-1.5 rounded-md bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors cursor-pointer"
          >
            {isDarkMode ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
      </div>
    </header>
  );
};
