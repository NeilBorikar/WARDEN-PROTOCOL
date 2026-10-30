import { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { type ScreenId } from './components/common/Header';
import { LiveRunScreen } from './components/screens/LiveRunScreen';
import { ApprovalsScreen } from './components/screens/ApprovalsScreen';
import { MandateScreen } from './components/screens/MandateScreen';
import { AuditScreen } from './components/screens/AuditScreen';
import { ResultsScreen } from './components/screens/ResultsScreen';
import { ArenaScreen } from './components/screens/ArenaScreen';
import { Splash, STAGGER_MS } from './components/common/Splash';
import { CommandPalette } from './components/common/CommandPalette';
import { api, DEMO_APPROVALS } from './api/client';
import { sounds } from './utils/audio';
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
  RotateCcw,
  Search,
  Lock,
} from 'lucide-react';
import './App.css';

export function App() {
  // Show splash once per session unless ?splash=1 is set
  const [showSplash, setShowSplash] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    const params = new URLSearchParams(window.location.search);
    if (params.get('splash') === '1') return true;
    return !sessionStorage.getItem('warden_splash_seen');
  });

  const [currentScreen, setCurrentScreen] = useState<ScreenId>('live-run');
  const [pendingCount, setPendingCount] = useState<number>(DEMO_APPROVALS.length);
  const [commandPrompt, setCommandPrompt] = useState<string>('');
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [dataReady, setDataReady] = useState<boolean>(false);

  const windowRef = useRef<HTMLDivElement>(null);
  const mainLandmarkRef = useRef<HTMLElement>(null);
  const telemetryRef = useRef<HTMLDivElement>(null);

  // Sync pending approvals count & mark dataReady for splash synchronizer
  const refreshPendingCount = async () => {
    try {
      const pending = await api.getApprovals('pending');
      setPendingCount(pending.length);
    } catch {
      setPendingCount(DEMO_APPROVALS.length);
    } finally {
      setDataReady(true);
    }
  };

  useEffect(() => {
    refreshPendingCount();
    const interval = setInterval(refreshPendingCount, 15000);
    return () => clearInterval(interval);
  }, []);

  // Subtle telemetry pulse
  useEffect(() => {
    if (!telemetryRef.current) return;
    const tween = gsap.to(telemetryRef.current, {
      y: -3,
      duration: 2.8,
      repeat: -1,
      yoyo: true,
      ease: 'sine.inOut',
    });
    return () => {
      tween.kill();
    };
  }, []);

  // Interactive Mouse Parallax for Background Ambience
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      const xRatio = (e.clientX - innerWidth / 2) / innerWidth;
      const yRatio = (e.clientY - innerHeight / 2) / innerHeight;

      gsap.to('.nixtio-curves', {
        x: xRatio * 20,
        y: yRatio * 20,
        duration: 1.2,
        ease: 'power2.out',
      });

      gsap.to('.nixtio-bg-svg', {
        x: xRatio * -24,
        y: yRatio * -24,
        duration: 1.5,
        ease: 'power2.out',
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Global Keyboard Shortcuts (Cmd/Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Ensure scroll is at the top on mount
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, []);

  // Reveal Dashboard after Splash Completes (3.0s - 3.8s)
  const handleSplashComplete = () => {
    sessionStorage.setItem('warden_splash_seen', 'true');
    setShowSplash(false);
    sounds.playBouncerOnline();

    // Ensure the viewport is pinned strictly to top
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    if (windowRef.current) {
      windowRef.current.style.visibility = 'visible';

      gsap.fromTo(
        windowRef.current,
        { opacity: 0, y: 8, filter: 'blur(6px)' },
        {
          opacity: 1,
          y: 0,
          filter: 'blur(0px)',
          duration: 0.8,
          ease: 'power2.out',
          onComplete: () => {
            mainLandmarkRef.current?.focus({ preventScroll: true });
            window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
          },
        }
      );
    }

    gsap.fromTo(
      '.sidebar-nav-btn',
      { opacity: 0, x: -14 },
      { opacity: 1, x: 0, stagger: 0.04, duration: 0.45, ease: 'back.out(1.5)', delay: 0.05 }
    );

    gsap.fromTo(
      '.nixtio-card',
      { opacity: 0, y: 12 },
      {
        opacity: 1,
        y: 0,
        stagger: STAGGER_MS / 1000,
        duration: 0.5,
        ease: 'power2.out',
        delay: 0.1,
      }
    );
  };

  // Replay Splash
  const handleReplaySplash = () => {
    setShowSplash(true);
  };

  // Screen Transitions: Scroll to top cleanly
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    if (mainLandmarkRef.current && !showSplash) {
      gsap.fromTo(
        mainLandmarkRef.current,
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: 0.28, ease: 'power2.out' }
      );
    }
  }, [currentScreen, showSplash]);

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
    if (!commandPrompt.trim()) {
      setIsCommandPaletteOpen(true);
      return;
    }

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
    <div className="min-h-screen text-slate-800 flex flex-col items-center justify-start py-2 sm:py-5 px-2 sm:px-5 relative overflow-hidden font-sans selection:bg-slate-900 selection:text-white">
      {/* Splash Screen (Removed from DOM after completion) */}
      {showSplash && (
        <Splash onComplete={handleSplashComplete} dataReady={dataReady} />
      )}

      {/* Cmd/Ctrl+K Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={(screen) => setCurrentScreen(screen)}
        onRunAttack={() => setCurrentScreen('live-run')}
        onVerifyChain={() => setCurrentScreen('audit')}
        onToggleBouncerView={() => setCurrentScreen('results')}
      />

      {/* Abstract curvy lines in the background matching palette */}
      <div className="nixtio-curves" />

      {/* Background SVG decorative curves with parallax class */}
      <svg
        className="nixtio-bg-svg fixed inset-0 w-full h-full pointer-events-none opacity-40 z-0"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M-100,200 C300,100 600,500 1200,200 C1500,50 1800,400 2000,300" fill="none" stroke="rgba(165,180,252,0.35)" strokeWidth="1.5" />
        <path d="M-100,400 C400,300 700,700 1300,400 C1600,250 1900,600 2200,500" fill="none" stroke="rgba(147,197,253,0.3)" strokeWidth="1.5" />
        <path d="M-50,600 C500,500 800,900 1400,600 C1700,450 2000,800 2300,700" fill="none" stroke="rgba(199,210,254,0.25)" strokeWidth="1.5" />
      </svg>

      {/* Main Dashboard Window */}
      <div
        ref={windowRef}
        style={{
          visibility: showSplash ? 'hidden' : 'visible',
          opacity: showSplash ? 0 : 1,
        }}
        className="nixtio-window w-full max-w-[97vw] xl:max-w-[1740px] 2xl:max-w-[1860px] rounded-[32px] sm:rounded-[44px] flex flex-col md:flex-row relative z-10 overflow-hidden my-0"
      >
        {/* Left Vertical Dock / Sidebar */}
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
          <nav className="flex md:flex-col items-center gap-2 sm:gap-3" aria-label="Main Navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentScreen(item.id)}
                  title={item.label}
                  aria-label={item.label}
                  className={`sidebar-nav-btn relative p-2.5 rounded-full transition-all cursor-pointer ${
                    isActive
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-800 hover:bg-slate-100'
                  }`}
                >
                  <Icon size={18} />
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-slate-900 text-white font-mono text-[9px] font-extrabold flex items-center justify-center">
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
          
          {/* Top Header Row */}
          <header className="flex items-center justify-between pb-5 border-b border-slate-150/80 mb-5">
            {/* Left: Pill Dropdown Badge */}
            <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-slate-100/80 border border-slate-200/80 text-xs font-semibold text-slate-700 shadow-2xs">
              <Sparkles size={14} className="text-slate-900" />
              <span>Warden Bouncer v0.1.0</span>
            </div>

            {/* Center: Command Palette Trigger Button */}
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="hidden sm:inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200/90 text-xs font-medium text-slate-500 hover:text-slate-800 hover:border-slate-300 transition-all cursor-pointer shadow-2xs"
            >
              <Search size={13} className="text-slate-400" />
              <span>Command Search</span>
              <kbd className="font-mono text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                ⌘K
              </kbd>
            </button>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleReplaySplash}
                title="Replay Minimalist Title Intro"
                className="px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-200 text-xs font-semibold text-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <RotateCcw size={12} className="text-slate-600" />
                <span className="hidden sm:inline">Intro</span>
              </button>
              <button
                onClick={() => setIsDemoMode(!isDemoMode)}
                className="nixtio-pill-dark px-4 py-2 text-xs font-semibold flex items-center gap-2 cursor-pointer"
              >
                <Radio size={12} className="text-blue-400 animate-pulse" />
                <span>{isDemoMode ? 'Cassette Replay' : 'Live PayPal Rail'}</span>
              </button>
            </div>
          </header>

          {/* Executive Security Attestation Banner (Clean, authoritative, zero cartoon emojis) */}
          <div className="relative mb-6">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="max-w-xl">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Ed25519 Cryptographic Boundary • Active
                  </span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 leading-tight">
                  Autonomous Spending Security Rail
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 mt-1 font-medium leading-relaxed">
                  Deterministic policy boundary enforcing owner-signed budget caps. Untrusted agent chat cannot exfiltrate PayPal credentials or exceed authorized limits.
                </p>
              </div>

              {/* Hardware / Cryptographic Policy Telemetry Badge */}
              <div
                ref={telemetryRef}
                className="flex items-center gap-3.5 p-3.5 rounded-2xl bg-white border border-slate-200/90 shadow-xs shrink-0 select-none"
              >
                <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0">
                  <Lock size={17} className="stroke-[2.2]" />
                </div>
                <div className="text-left font-mono">
                  <div className="text-[10px] uppercase text-slate-400 font-bold tracking-wider">
                    Root of Trust
                  </div>
                  <div className="text-xs font-extrabold text-slate-900">
                    key-owner-ed25519-1
                  </div>
                  <div className="text-[10px] text-slate-500 flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                    <span>Velocity: 0/5 tx/hr</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Active Screen Viewport (Main Landmark with focus target for a11y) */}
          <main
            ref={mainLandmarkRef}
            tabIndex={-1}
            aria-label="Warden Security Workspace"
            className="flex-1 min-h-[460px] pb-6 outline-hidden"
          >
            {currentScreen === 'live-run' && <LiveRunScreen />}
            {currentScreen === 'approvals' && (
              <ApprovalsScreen onApprovalResolved={refreshPendingCount} />
            )}
            {currentScreen === 'mandates' && <MandateScreen />}
            {currentScreen === 'audit' && <AuditScreen />}
            {currentScreen === 'results' && <ResultsScreen />}
            {currentScreen === 'arena' && <ArenaScreen />}
          </main>

          {/* Bottom Floating Pill Command Input Bar */}
          <footer className="mt-auto pt-4 border-t border-slate-150/80">
            <form
              onSubmit={handleCommandSubmit}
              onClick={() => {
                if (!commandPrompt) setIsCommandPaletteOpen(true);
              }}
              className="nixtio-command-pill w-full rounded-full p-2 pl-4 flex items-center gap-3 shadow-md"
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsCommandPaletteOpen(true);
                }}
                className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center transition-colors cursor-pointer shrink-0"
                title="Open Command Palette (⌘K)"
              >
                <Plus size={16} />
              </button>

              <input
                type="text"
                value={commandPrompt}
                onChange={(e) => setCommandPrompt(e.target.value)}
                placeholder='Type a command or press ⌘K (e.g. "Run attack simulation" or "Review pending approvals")...'
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
                <span>Execute Scenario</span>
              </button>

              <button
                onClick={() => setCurrentScreen('approvals')}
                className="nixtio-pill-dark px-3.5 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <CheckCircle size={12} />
                <span>Pending Approvals ({pendingCount})</span>
              </button>

              <button
                onClick={() => setCurrentScreen('audit')}
                className="nixtio-pill-dark px-3.5 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <History size={12} />
                <span>Verify Preimages</span>
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
                <span>45-Scenario Matrix</span>
              </button>
            </div>
          </footer>

        </div>
      </div>
    </div>
  );
}

export default App;
