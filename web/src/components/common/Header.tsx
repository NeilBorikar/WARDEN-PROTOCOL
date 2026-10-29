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
  Radio,
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
  const navItems: Array<{
    id: ScreenId;
    label: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    badge?: number;
  }> = [
    { id: 'live-run', label: 'Live Run', icon: Activity },
    { id: 'approvals', label: 'Approvals', icon: CheckCircle, badge: pendingApprovalsCount },
    { id: 'mandates', label: 'Mandates & Intent', icon: FileCode2 },
    { id: 'audit', label: 'Audit Chain', icon: History },
    { id: 'results', label: 'Benchmark', icon: BarChart3 },
    { id: 'arena', label: 'Adversarial Arena', icon: Swords },
  ];

  return (
    <header className="sticky top-0 z-50 transition-colors duration-200 border-b border-slate-200/80 dark:border-white/[0.08] bg-white/75 dark:bg-slate-950/75 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          
          {/* Brand & Security Status Pill */}
          <div className="flex items-center justify-between w-full md:w-auto gap-4">
            <div className="flex items-center gap-3">
              <div className="relative group cursor-pointer" onClick={() => onSelectScreen('live-run')}>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 p-0.5 shadow-md shadow-blue-500/20">
                  <div className="w-full h-full bg-slate-950 dark:bg-slate-900 rounded-[10px] flex items-center justify-center text-blue-400 group-hover:text-white transition-colors">
                    <Shield size={20} className="stroke-[2.5]" />
                  </div>
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-600 rounded-full border-2 border-white animate-ping opacity-75" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-600 rounded-full border-2 border-white" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="font-extrabold tracking-tight text-sm sm:text-base text-slate-900">
                    WARDEN PROTOCOL
                  </span>
                  <span className="px-1.5 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-600 text-[10px] font-mono rounded-md font-bold">
                    v0.1.0
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-medium">
                  <span>PayPal AI Security Console</span>
                  <span className="text-slate-300">•</span>
                  <span className="text-blue-600 font-semibold flex items-center gap-1">
                    <Radio size={10} className="animate-pulse" /> Fail-Closed
                  </span>
                </div>
              </div>
            </div>

            {/* Mobile quick controls */}
            <div className="flex items-center gap-2 md:hidden">
              <button
                onClick={onToggleDemoMode}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-white/10 text-xs font-mono"
              >
                <Flame size={14} className={isDemoMode ? 'text-purple-500' : 'text-slate-400'} />
              </button>
              <button
                onClick={onToggleTheme}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-white/10 text-xs"
              >
                {isDarkMode ? <Sun size={14} /> : <Moon size={14} />}
              </button>
            </div>
          </div>

          {/* Navigation Pill Bar */}
          <nav aria-label="Main Navigation" className="flex items-center gap-1 p-1 rounded-2xl bg-slate-200/50 dark:bg-slate-900/80 border border-slate-300/50 dark:border-white/[0.06] overflow-x-auto max-w-full scrollbar-none shadow-inner">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectScreen(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 shrink-0 cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/25'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Icon size={14} className={isActive ? 'text-white' : 'text-slate-400 dark:text-slate-400'} />
                  <span>{item.label}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span
                      className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold leading-tight ${
                        isActive
                          ? 'bg-white text-blue-700'
                          : 'bg-amber-500 text-slate-950 shadow-xs'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Global Utility Actions */}
          <div className="hidden md:flex items-center gap-2.5">
            {/* Mode switch (Cassette vs Live API) */}
            <button
              onClick={onToggleDemoMode}
              title={isDemoMode ? 'Cassette Replay Mode Active' : 'Live API Backend Active'}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-mono font-medium border transition-all cursor-pointer shadow-xs ${
                isDemoMode
                  ? 'bg-purple-500/10 dark:bg-purple-500/15 border-purple-500/30 text-purple-600 dark:text-purple-300 shadow-purple-500/5'
                  : 'bg-white/80 dark:bg-slate-900 border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Flame size={13} className={isDemoMode ? 'text-purple-500 animate-pulse' : 'text-slate-400'} />
              <span>{isDemoMode ? 'Cassette Demo' : 'Live API'}</span>
            </button>

            {/* Theme Toggle Button */}
            <button
              onClick={onToggleTheme}
              aria-label="Toggle visual theme"
              className="p-2 rounded-xl bg-white/80 dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer shadow-xs"
            >
              {isDarkMode ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-indigo-600" />}
            </button>
          </div>

        </div>
      </div>
    </header>
  );
};
