import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { Shield, Lock, Cpu, Sparkles } from 'lucide-react';

interface EliteIntroSplashProps {
  onComplete: () => void;
}

export const EliteIntroSplash: React.FC<EliteIntroSplashProps> = ({ onComplete }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const logoRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const progressTextRef = useRef<HTMLSpanElement>(null);
  const statusStepRef = useRef<HTMLDivElement>(null);
  const orbitRef = useRef<SVGSVGElement>(null);

  const [progress, setProgress] = useState<number>(0);
  const [statusMsg, setStatusMsg] = useState<string>('SYNCHRONIZING POLICY ENGINE');

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        onComplete: () => {
          // Fade and slide the whole splash up
          gsap.to(containerRef.current, {
            yPercent: -100,
            opacity: 0.9,
            duration: 0.95,
            ease: 'power4.inOut',
            onComplete: () => {
              onComplete();
            },
          });
        },
      });

      // 1. Initial State
      gsap.set(logoRef.current, { scale: 0.6, opacity: 0 });
      gsap.set(titleRef.current, { opacity: 0, y: 24, letterSpacing: '0.4em' });
      gsap.set(subtitleRef.current, { opacity: 0, y: 16 });
      gsap.set(barRef.current, { width: '0%' });

      // Ambient Orbit Rotation
      if (orbitRef.current) {
        gsap.to(orbitRef.current, {
          rotation: 360,
          duration: 20,
          repeat: -1,
          ease: 'none',
          transformOrigin: '50% 50%',
        });
      }

      // 2. Entrance sequence
      tl.to(logoRef.current, {
        scale: 1,
        opacity: 1,
        duration: 0.7,
        ease: 'back.out(1.7)',
      })
      .to(
        titleRef.current,
        {
          opacity: 1,
          y: 0,
          duration: 0.65,
          ease: 'power3.out',
        },
        '-=0.35'
      )
      .to(
        subtitleRef.current,
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          ease: 'power2.out',
        },
        '-=0.25'
      );

      // 3. Progress bar fill & status progression
      const progressObj = { value: 0 };
      tl.to(
        progressObj,
        {
          value: 100,
          duration: 1.6,
          ease: 'power2.inOut',
          onUpdate: () => {
            const val = Math.round(progressObj.value);
            setProgress(val);
            if (barRef.current) {
              barRef.current.style.width = `${val}%`;
            }
            if (val > 25 && val < 60) {
              setStatusMsg('VERIFYING ED25519 CRYPTOGRAPHIC MANDATES');
            } else if (val >= 60 && val < 90) {
              setStatusMsg('ARMING DETERMINISTIC BOUNCER RAIL');
            } else if (val >= 90) {
              setStatusMsg('AUTONOMOUS POLICY VERIFIED • READY');
            }
          },
        },
        '-=0.2'
      );

      // 4. Climax pulse before reveal
      tl.to(logoRef.current, {
        scale: 1.08,
        duration: 0.2,
        ease: 'power1.out',
      })
      .to(logoRef.current, {
        scale: 1,
        duration: 0.25,
        ease: 'power2.in',
      });
    }, containerRef);

    return () => ctx.revert();
  }, [onComplete]);

  const handleSkip = () => {
    gsap.to(containerRef.current, {
      yPercent: -100,
      opacity: 0,
      duration: 0.5,
      ease: 'power3.inOut',
      onComplete,
    });
  };

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-50 bg-[#090D16] text-white flex flex-col items-center justify-center overflow-hidden select-none"
    >
      {/* Background ambient glowing orbs */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[650px] bg-blue-600/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Subtle background tech grid */}
      <div
        className="absolute inset-0 opacity-[0.035] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      {/* Top Bar with Skip Button */}
      <div className="absolute top-6 right-8 z-10 flex items-center gap-3">
        <button
          onClick={handleSkip}
          className="text-[11px] font-mono uppercase tracking-widest text-slate-400 hover:text-white px-3.5 py-1.5 rounded-full border border-slate-800 hover:border-slate-600 bg-slate-900/60 backdrop-blur-md transition-all cursor-pointer"
        >
          Skip Intro ↵
        </button>
      </div>

      {/* Center Cinematic Container */}
      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-lg">
        
        {/* Glowing Shield Icon with Orbital Rings */}
        <div className="relative mb-8">
          {/* Animated SVG Orbit Ring */}
          <svg
            ref={orbitRef}
            className="absolute -inset-6 w-[124px] h-[124px] pointer-events-none opacity-60"
            viewBox="0 0 100 100"
          >
            <circle
              cx="50"
              cy="50"
              r="46"
              fill="none"
              stroke="rgba(99, 102, 241, 0.4)"
              strokeWidth="1.2"
              strokeDasharray="6 8"
            />
            <circle cx="50" cy="4" r="3" fill="#60A5FA" />
            <circle cx="50" cy="96" r="2.5" fill="#818CF8" />
          </svg>

          {/* Central Logo Badge */}
          <div
            ref={logoRef}
            className="w-19 h-19 rounded-3xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-700/80 shadow-[0_0_50px_rgba(59,130,246,0.35)] flex items-center justify-center relative z-10"
          >
            <Shield className="w-9 h-9 text-blue-400 stroke-[2.2]" />
            <Sparkles className="w-4 h-4 text-indigo-300 absolute -top-1 -right-1 animate-pulse" />
          </div>
        </div>

        {/* Title */}
        <h1
          ref={titleRef}
          className="text-3xl sm:text-4xl font-black font-sans tracking-[0.25em] uppercase text-transparent bg-clip-text bg-gradient-to-b from-white via-slate-150 to-slate-400 drop-shadow-sm mb-3"
        >
          Warden Protocol
        </h1>

        {/* Subtitle */}
        <div
          ref={subtitleRef}
          className="flex items-center gap-2 text-xs sm:text-sm font-medium text-slate-400 tracking-wider mb-8"
        >
          <Lock className="w-3.5 h-3.5 text-blue-400" />
          <span>Autonomous Errand Security & Deterministic Bouncer</span>
        </div>

        {/* Progress Bar & Status Text */}
        <div className="w-full max-w-xs space-y-3">
          {/* Thin Progress Track */}
          <div className="w-full h-1.5 rounded-full bg-slate-800/80 overflow-hidden border border-slate-800 p-[1px]">
            <div
              ref={barRef}
              className="h-full rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-sky-400 shadow-[0_0_12px_rgba(96,165,250,0.8)] transition-all"
            />
          </div>

          {/* Dynamic Percentage & Engine Status */}
          <div className="flex items-center justify-between text-[11px] font-mono">
            <div
              ref={statusStepRef}
              className="flex items-center gap-1.5 text-slate-400 text-left truncate max-w-[210px]"
            >
              <Cpu className="w-3 h-3 text-blue-400 shrink-0 animate-spin" />
              <span className="truncate">{statusMsg}</span>
            </div>
            <span
              ref={progressTextRef}
              className="font-bold text-blue-400 tabular-nums ml-2"
            >
              {progress}%
            </span>
          </div>
        </div>

      </div>

      {/* Bottom Minimalist Watermark */}
      <div className="absolute bottom-6 text-[10px] font-mono tracking-widest text-slate-600 uppercase">
        Deterministic Ed25519 Zero-Trust Runtime • v0.1.0
      </div>
    </div>
  );
};
