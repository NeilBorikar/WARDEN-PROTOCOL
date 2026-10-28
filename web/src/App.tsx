import { useState, useEffect } from 'react';
import { Header, type ScreenId } from './components/common/Header';
import { LiveRunScreen } from './components/screens/LiveRunScreen';
import { ApprovalsScreen } from './components/screens/ApprovalsScreen';
import { MandateScreen } from './components/screens/MandateScreen';
import { AuditScreen } from './components/screens/AuditScreen';
import { ResultsScreen } from './components/screens/ResultsScreen';
import { ArenaScreen } from './components/screens/ArenaScreen';
import { api, DEMO_APPROVALS } from './api/client';
import { Shield, Lock } from 'lucide-react';

export function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('live-run');
  const [pendingCount, setPendingCount] = useState<number>(DEMO_APPROVALS.length);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);

  // Sync pending approvals count
  const refreshPendingCount = async () => {
    try {
      const pending = await api.getApprovals('pending');
      setPendingCount(pending.length);
    } catch {
      setPendingCount(DEMO_APPROVALS.length);
    }
  };

  useEffect(() => {
    refreshPendingCount();
    const interval = setInterval(refreshPendingCount, 15000);
    return () => clearInterval(interval);
  }, []);

  const toggleTheme = () => {
    setIsDarkMode((prev) => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return next;
    });
  };

  const toggleDemoMode = () => {
    setIsDemoMode((prev) => !prev);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Security Header */}
      <Header
        currentScreen={currentScreen}
        onSelectScreen={setCurrentScreen}
        pendingApprovalsCount={pendingCount}
        isDarkMode={isDarkMode}
        onToggleTheme={toggleTheme}
        isDemoMode={isDemoMode}
        onToggleDemoMode={toggleDemoMode}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {currentScreen === 'live-run' && <LiveRunScreen />}
        {currentScreen === 'approvals' && (
          <ApprovalsScreen onApprovalResolved={refreshPendingCount} />
        )}
        {currentScreen === 'mandates' && <MandateScreen />}
        {currentScreen === 'audit' && <AuditScreen />}
        {currentScreen === 'results' && <ResultsScreen />}
        {currentScreen === 'arena' && <ArenaScreen />}
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 text-xs text-slate-400 py-6 px-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield size={16} className="text-blue-500" />
            <span className="font-semibold text-slate-200">Warden Protocol</span>
            <span>—</span>
            <span>Deterministic AI Spending Safety Layer for PayPal</span>
          </div>

          <div className="flex items-center gap-6 font-mono text-[11px]">
            <span className="text-emerald-400 flex items-center gap-1">
              <Lock size={12} /> Worst-case loss: $0.00
            </span>
            <span className="text-slate-400">PayPal AI Hackathon 2026</span>
            <span className="text-slate-400">MIT Open Source</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
