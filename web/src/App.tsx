import { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { type ScreenId } from './components/common/Header';
import { LiveRunScreen } from './components/screens/LiveRunScreen';
import { ApprovalsScreen } from './components/screens/ApprovalsScreen';
import { MandateScreen } from './components/screens/MandateScreen';
import { AuditScreen } from './components/screens/AuditScreen';
import { ResultsScreen } from './components/screens/ResultsScreen';
import { ArenaScreen } from './components/screens/ArenaScreen';
import { api, DEMO_APPROVALS } from './api/client';
import {
  Shield,
  Activity,
  CheckCircle,
  FileCode2,
  History,
  BarChart3,
  Swords,
  Plus,
  Radio,
  Sparkles,
  ArrowUp,
  Mic,
  Zap,
  Lock,
} from 'lucide-react';
import './App.css';

export function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('live-run');
  const [pendingCount, setPendingCount] = useState<number>(DEMO_APPROVALS.length);
  const [commandPrompt, setCommandPrompt] = useState<string>('');
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);

  const windowRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLElement>(null);
  const mascotRef = useRef<HTMLDivElement>(null);

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

  // GSAP: Initial Page & Window Mount Entrance
  useEffect(() => {
    if (windowRef.current) {
      gsap.from(windowRef.current, {
        opacity: 0,
        y: 28,
        scale: 0.985,
        duration: 0.85,
        ease: 'power3.out',
      });
    }

    gsap.from('.sidebar-nav-btn', {
      opacity: 0,
      x: -15,
      stagger: 0.05,
      duration: 0.5,
      ease: 'back.out(1.5)',
      delay: 0.2,
    });

    if (mascotRef.current) {
      gsap.to(mascotRef.current, {
        y: -7,
        duration: 2.4,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
      });
    }
  }, []);

  // GSAP: Smooth Screen Transition
  useEffect(() => {
    if (contentRef.current) {
      gsap.fromTo(
        contentRef.current,
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, duration: 0.38, ease: 'power2.out' }
      );
    }
  }, [currentScreen]);

  const navItems: Array<{
    id: ScreenId;
    label: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    badge?: number;
  }> = [
    { id: 'live-run', label: 'Live Run', icon: Activity },
    { id: 'approvals', label: 'Approvals', icon: CheckCircle, badge: pendingCount },
    { id: 'mandates', label: 'Mandates', icon: FileCode2 },
    { id: 'audit', label: 'Audit Chain', icon: History },
    { id: 'results', label: 'Benchmark', icon: BarChart3 },
    { id: 'arena', label: 'Arena', icon: Swords },
  ];

  const handleCommandSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commandPrompt.trim()) return;

    const lower = commandPrompt.toLowerCase();
    if (lower.includes('approval') || lower.includes('pending')) {
      setCurrentScreen('approvals');
    } else if (lower.includes('mandate') || lower.includes('intent') || lower.includes('cap')) {
      setCurrentScreen('mandates');
    } else if (lower.includes('audit') || lower.includes('hash') || lower.includes('chain')) {
      setCurrentScreen('audit');
    } else if (lower.includes('benchmark') || lower.includes('result') || lower.includes('stats')) {
      setCurrentScreen('results');
    } else if (lower.includes('arena') || lower.includes('attack') || lower.includes('injection')) {
      setCurrentScreen('arena');
    } else {
      setCurrentScreen('live-run');
    }
    setCommandPrompt('');
  };

  return (
    <div className="min-h-screen text-slate-800 flex flex-col items-center justify-start py-3 sm:py-6 px-3 sm:px-6 relative overflow-hidden font-sans selection:bg-slate-900 selection:text-white">
      {/* Abstract curvy lines in the background matching Nixtio shot */}
      <div className="nixtio-curves" />

      {/* Background SVG decorative curves */}
      <svg className="fixed inset-0 w-full h-full pointer-events-none opacity-40 z-0" xmlns="http://www.w3.org/2000/svg">
        <path d="M-100,200 C300,100 600,500 1200,200 C1500,50 1800,400 2000,300" fill="none" stroke="rgba(165,180,252,0.35)" strokeWidth="1.5" />
        <path d="M-100,400 C400,300 700,700 1300,400 C1600,250 1900,600 2200,500" fill="none" stroke="rgba(147,197,253,0.3)" strokeWidth="1.5" />
        <path d="M-50,600 C500,500 800,900 1400,600 C1700,450 2000,800 2300,700" fill="none" stroke="rgba(199,210,254,0.25)" strokeWidth="1.5" />
      </svg>

      {/* Main Nixtio Floating App Window (Generous Widescreen Canvas) */}
      <div
        ref={windowRef}
        className="nixtio-window w-full max-w-[97vw] xl:max-w-[1740px] 2xl:max-w-[1860px] rounded-[32px] sm:rounded-[44px] flex flex-col md:flex-row relative z-10 overflow-hidden my-auto"
      >
        {/* Left Vertical Dock / Sidebar (Identical to Nixtio shot) */}
        <aside className="w-full md:w-20 bg-white/75 border-b md:border-b-0 md:border-r border-slate-200/70 flex md:flex-col items-center justify-between p-3 sm:p-5 shrink-0 backdrop-blur-md">
          {/* Top Round Black Plus Action Button */}
          <button
            onClick={() => setCurrentScreen('live-run')}
            title="Start New Live Run"
            className="w-10 h-10 rounded-full bg-slate-900 hover:bg-black text-white flex items-center justify-center shadow-md hover:scale-105 transition-all cursor-pointer shrink-0"
          >
            <Plus size={18} className="stroke-[2.5]" />
          </button>

          {/* Center Navigation Icons */}
          <nav className="flex md:flex-col items-center gap-2 sm:gap-3">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentScreen(item.id)}
                  title={item.label}
                  className={`sidebar-nav-btn relative p-2.5 rounded-full transition-all cursor-pointer ${
                    isActive
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-800 hover:bg-slate-100'
                  }`}
                >
                  <Icon size={18} />
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-500 text-slate-950 font-mono text-[9px] font-extrabold flex items-center justify-center">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Bottom Black Rounded Square Logo Mark */}
          <button
            onClick={() => setCurrentScreen('live-run')}
            title="Warden Protocol Home"
            className="w-10 h-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center shadow-md hover:bg-black transition-all cursor-pointer shrink-0"
          >
            <Shield size={18} className="stroke-[2.5]" />
          </button>
        </aside>

        {/* Center Main Workspace Content Area */}
        <div className="flex-1 flex flex-col p-4 sm:p-7 lg:p-9 min-w-0">
          
          {/* Top Header Row (Identical to Nixtio shot) */}
          <header className="flex items-center justify-between pb-6 border-b border-slate-150/80 mb-6">
            {/* Left: Pill Dropdown Badge */}
            <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-slate-100/80 border border-slate-200/80 text-xs font-semibold text-slate-700 shadow-2xs">
              <Sparkles size={14} className="text-slate-900" />
              <span>Warden Bouncer v0.1.0</span>
            </div>

            {/* Center: Title / Context */}
            <span className="text-xs font-semibold text-slate-400 tracking-wide uppercase font-mono hidden sm:inline">
              Autonomous Spending Security Console
            </span>

            {/* Right: Black Pill Action Button */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsDemoMode(!isDemoMode)}
                className="nixtio-pill-dark px-4 py-2 text-xs font-semibold flex items-center gap-2 cursor-pointer"
              >
                <Radio size={12} className="text-blue-400 animate-pulse" />
                <span>{isDemoMode ? 'Cassette Replay' : 'Live PayPal Rail'}</span>
              </button>
            </div>
          </header>

          {/* Hero Greeting & Cute AI Robot Mascot */}
          <div className="relative mb-7">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="max-w-xl">
                <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
                  Hi Alice, Ready to Secure Autonomous Errand Payments?
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 mt-2 font-medium">
                  Deterministic Ed25519 spending mandates enforce strict budget caps. Untrusted chat cannot steal funds.
                </p>
              </div>

              {/* Cute 3D AI Robot Mascot & Speech Bubble */}
              <div ref={mascotRef} className="relative flex items-center self-end lg:self-center shrink-0 pr-4">
                {/* Speech Bubble */}
                <div className="absolute -top-6 -left-28 bg-white border border-slate-200 shadow-md rounded-2xl px-3 py-1.5 text-[11px] font-semibold text-slate-800 whitespace-nowrap">
                  Hey Alice! 👋 Need a safety check?
                  <div className="absolute -bottom-1.5 right-6 w-3 h-3 bg-white border-r border-b border-slate-200 rotate-45" />
                </div>

                {/* 3D Robot Vector Illustration */}
                <svg width="76" height="76" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="drop-shadow-lg">
                  <ellipse cx="50" cy="94" rx="28" ry="4" fill="rgba(100,116,139,0.18)" />
                  <rect x="28" y="52" width="44" height="34" rx="17" fill="url(#bot_body)" />
                  <rect x="34" y="58" width="32" height="22" rx="11" fill="#FFFFFF" />
                  <circle cx="50" cy="69" r="5" fill="#3B82F6" />
                  <rect x="44" y="46" width="12" height="8" rx="4" fill="#94A3B8" />
                  <rect x="20" y="16" width="60" height="34" rx="17" fill="url(#bot_head)" stroke="#E2E8F0" strokeWidth="1.5" />
                  <rect x="26" y="21" width="48" height="24" rx="12" fill="#0F172A" />
                  <ellipse cx="40" cy="33" rx="5" ry="4" fill="#38BDF8" />
                  <ellipse cx="60" cy="33" rx="5" ry="4" fill="#38BDF8" />
                  <rect x="48" y="8" width="4" height="9" rx="2" fill="#94A3B8" />
                  <circle cx="50" cy="7" r="4" fill="#3B82F6" />
                  <defs>
                    <linearGradient id="bot_head" x1="20" y1="16" x2="80" y2="50" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#FFFFFF" />
                      <stop offset="1" stopColor="#E2E8F0" />
                    </linearGradient>
                    <linearGradient id="bot_body" x1="28" y1="52" x2="72" y2="86" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#F8FAFC" />
                      <stop offset="1" stopColor="#CBD5E1" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>
          </div>

          {/* Active Screen Viewport with GSAP ref */}
          <main ref={contentRef} className="flex-1 min-h-[460px] pb-6">
            {currentScreen === 'live-run' && <LiveRunScreen />}
            {currentScreen === 'approvals' && (
              <ApprovalsScreen onApprovalResolved={refreshPendingCount} />
            )}
            {currentScreen === 'mandates' && <MandateScreen />}
            {currentScreen === 'audit' && <AuditScreen />}
            {currentScreen === 'results' && <ResultsScreen />}
            {currentScreen === 'arena' && <ArenaScreen />}
          </main>

          {/* Bottom AI Command Bar & Action Pills (Exact Nixtio pattern) */}
          <footer className="pt-5 border-t border-slate-150/80">
            {/* Top Caption Row */}
            <div className="flex items-center justify-between text-[11px] font-medium text-slate-400 mb-2.5 px-2">
              <span className="flex items-center gap-1.5 text-slate-600 font-semibold">
                <Lock size={12} className="text-blue-600" />
                Owner-Signed Ed25519 Spending Security
              </span>
              <span>Worst-case loss strictly capped at $0.00</span>
            </div>

            {/* Input Pill Bar */}
            <form onSubmit={handleCommandSubmit} className="nixtio-command-pill rounded-full px-4 py-2 flex items-center gap-3 shadow-sm">
              <button
                type="button"
                onClick={() => setCurrentScreen('live-run')}
                className="text-slate-400 hover:text-slate-900 p-1 rounded-full transition-colors cursor-pointer"
                title="Quick Action"
              >
                <Plus size={16} />
              </button>

              <input
                type="text"
                value={commandPrompt}
                onChange={(e) => setCommandPrompt(e.target.value)}
                placeholder='Example : "Simulate prompt injection attack against buyer agent" or "Review pending approvals"'
                className="flex-1 bg-transparent text-xs text-slate-800 placeholder:text-slate-400 focus:outline-hidden font-medium"
              />

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  title="Voice Command"
                  className="p-1.5 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
                >
                  <Mic size={15} />
                </button>
                <button
                  type="submit"
                  title="Execute Instruction"
                  className="w-8 h-8 rounded-full bg-slate-900 hover:bg-black text-white flex items-center justify-center transition-all cursor-pointer shadow-xs hover:scale-105"
                >
                  <ArrowUp size={15} className="stroke-[2.5]" />
                </button>
              </div>
            </form>

            {/* Quick Action Pill Buttons */}
            <div className="flex flex-wrap items-center gap-2 mt-3 px-1">
              <button
                onClick={() => setCurrentScreen('live-run')}
                className="nixtio-pill-dark px-3.5 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <Zap size={12} />
                <span>Simulate Negotiation</span>
              </button>

              <button
                onClick={() => setCurrentScreen('approvals')}
                className="nixtio-pill-dark px-3.5 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <CheckCircle size={12} />
                <span>Review Approvals ({pendingCount})</span>
              </button>

              <button
                onClick={() => setCurrentScreen('audit')}
                className="nixtio-pill-dark px-3.5 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <History size={12} />
                <span>Verify Preimage Chain</span>
              </button>

              <button
                onClick={() => setCurrentScreen('arena')}
                className="nixtio-pill-dark px-3.5 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <Swords size={12} />
                <span>Adversarial Arena</span>
              </button>

              <button
                onClick={() => setCurrentScreen('results')}
                className="px-3.5 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold border border-slate-200 transition-all cursor-pointer"
              >
                <span>Benchmark Matrix</span>
              </button>
            </div>
          </footer>

        </div>
      </div>
    </div>
  );
}

export default App;
