import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';

export const SPLASH_TOTAL_MS = 3200;
export const BAR_MS = 1600;
export const STAGGER_MS = 60;

interface SplashProps {
  onComplete: () => void;
  dataReady?: boolean;
}

export const Splash: React.FC<SplashProps> = ({ onComplete, dataReady = true }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const shieldPathRef = useRef<SVGPathElement>(null);
  const wordmarkRef = useRef<HTMLDivElement>(null);
  const barTrackRef = useRef<HTMLDivElement>(null);
  const barFillRef = useRef<HTMLDivElement>(null);
  const barGlowRef = useRef<HTMLDivElement>(null);
  const captionRef = useRef<HTMLParagraphElement>(null);

  const [captionText, setCaptionText] = useState<string>('VERIFYING MANDATE SIGNATURE...');
  const tlRef = useRef<gsap.core.Timeline | null>(null);
  const dataReadyRef = useRef<boolean>(dataReady);

  useEffect(() => {
    dataReadyRef.current = dataReady;
  }, [dataReady]);

  useEffect(() => {
    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Lock body scroll
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Failsafe 6s timer
    const failsafe = setTimeout(() => {
      handleFinish();
    }, 6000);

    const handleFinish = () => {
      document.body.style.overflow = originalOverflow;
      clearTimeout(failsafe);
      onComplete();
    };

    if (prefersReducedMotion) {
      // 300ms gentle crossfade for reduced motion
      const quickTl = gsap.timeline({
        onComplete: handleFinish,
      });
      quickTl.to(containerRef.current, {
        opacity: 0,
        duration: 0.3,
        ease: 'power1.inOut',
      });
      return () => {
        document.body.style.overflow = originalOverflow;
        clearTimeout(failsafe);
        quickTl.kill();
      };
    }

    // Set up stroke-dashoffset on the shield outline
    if (shieldPathRef.current) {
      const length = shieldPathRef.current.getTotalLength();
      gsap.set(shieldPathRef.current, {
        strokeDasharray: length,
        strokeDashoffset: length,
        opacity: 0,
      });
    }

    // Initial states: 0.0-0.4s pure dashboard background, nothing visible
    gsap.set(wordmarkRef.current, {
      opacity: 0,
      filter: 'blur(8px)',
      letterSpacing: '0.5em',
    });
    gsap.set([barTrackRef.current, captionRef.current], {
      opacity: 0,
    });
    gsap.set(barFillRef.current, {
      width: '0%',
    });
    gsap.set(barGlowRef.current, {
      left: '0%',
      opacity: 0,
    });

    const masterTl = gsap.timeline({
      onComplete: handleFinish,
    });
    tlRef.current = masterTl;

    // 0.4s - 0.9s: Shield outline draws, wordmark fades in with blur reduction
    masterTl.addLabel('iconReveal', 0.4);
    if (shieldPathRef.current) {
      masterTl.to(
        shieldPathRef.current,
        {
          strokeDashoffset: 0,
          opacity: 1,
          duration: 0.5,
          ease: 'power2.out',
        },
        'iconReveal'
      );
    }

    masterTl.to(
      wordmarkRef.current,
      {
        opacity: 1,
        filter: 'blur(0px)',
        letterSpacing: '0.32em',
        duration: 0.5,
        ease: 'power2.out',
      },
      'iconReveal+=0.05'
    );

    // 0.9s - 2.5s: Slim bar fills with non-linear easing; caption cycles
    masterTl.addLabel('barStart', 0.9);
    masterTl.to(
      [barTrackRef.current, captionRef.current],
      {
        opacity: 1,
        duration: 0.25,
        ease: 'power1.out',
      },
      'barStart'
    );

    masterTl.to(
      barGlowRef.current,
      {
        opacity: 0.7,
        duration: 0.2,
      },
      'barStart'
    );

    // Custom non-linear bar fill: fast to 40% (0.4s), slow to 78% (0.7s), brief pause (0.15s), then finish (0.35s) = 1.6s (BAR_MS)
    const barProgress = { value: 0 };
    masterTl.to(
      barProgress,
      {
        value: 40,
        duration: 0.4,
        ease: 'power2.out',
        onUpdate: () => {
          if (barFillRef.current && barGlowRef.current) {
            barFillRef.current.style.width = `${barProgress.value}%`;
            barGlowRef.current.style.left = `${barProgress.value}%`;
          }
        },
      },
      'barStart'
    );

    masterTl.call(() => {
      setCaptionText('LOADING POLICY ENGINE (C1-C8)...');
    }, undefined, 'barStart+=0.4');

    masterTl.to(
      barProgress,
      {
        value: 78,
        duration: 0.7,
        ease: 'power1.inOut',
        onUpdate: () => {
          if (barFillRef.current && barGlowRef.current) {
            barFillRef.current.style.width = `${barProgress.value}%`;
            barGlowRef.current.style.left = `${barProgress.value}%`;
          }
        },
      },
      'barStart+=0.4'
    );

    masterTl.call(() => {
      setCaptionText('SEALING AUDIT CHAIN...');
    }, undefined, 'barStart+=1.1');

    // Brief pause (0.15s), then finish to 100%
    masterTl.to(
      barProgress,
      {
        value: 100,
        duration: 0.35,
        ease: 'power3.out',
        onUpdate: () => {
          if (barFillRef.current && barGlowRef.current) {
            barFillRef.current.style.width = `${barProgress.value}%`;
            barGlowRef.current.style.left = `${barProgress.value}%`;
          }
        },
      },
      'barStart+=1.25'
    );

    masterTl.call(() => {
      setCaptionText('BOUNCER ONLINE');
    }, undefined, 'barStart+=1.55');

    // 2.5s - 2.8s: Bar hits 100%, bar + caption fade out, wordmark pulses once
    masterTl.addLabel('pulse', 2.5);
    masterTl.to(
      [barTrackRef.current, captionRef.current, barGlowRef.current],
      {
        opacity: 0,
        duration: 0.25,
        ease: 'power1.in',
      },
      'pulse'
    );

    masterTl.to(
      [wordmarkRef.current, shieldPathRef.current?.parentElement],
      {
        scale: 1.05,
        duration: 0.15,
        ease: 'power1.out',
        yoyo: true,
        repeat: 1,
      },
      'pulse'
    );

    // 2.8s - 3.2s: Splash fades out (opacity 1->0, scale 1->1.04)
    masterTl.addLabel('fadeOut', 2.8);
    masterTl.to(
      containerRef.current,
      {
        opacity: 0,
        scale: 1.04,
        duration: 0.4,
        ease: 'power2.inOut',
      },
      'fadeOut'
    );

    // Skip on click or any keypress
    const handleSkip = () => {
      if (masterTl) {
        masterTl.timeScale(4); // Accelerates smoothly to the end
      }
    };

    const containerEl = containerRef.current;
    if (containerEl) {
      containerEl.addEventListener('click', handleSkip);
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        handleSkip();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      clearTimeout(failsafe);
      if (containerEl) {
        containerEl.removeEventListener('click', handleSkip);
      }
      window.removeEventListener('keydown', handleKeyDown);
      masterTl.kill();
    };
  }, [onComplete]);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center select-none cursor-pointer overflow-hidden"
      style={{
        backgroundColor: '#E8EEFB',
        backgroundImage: `
          radial-gradient(circle at 12% 18%, rgba(200, 218, 255, 0.75) 0%, transparent 45%),
          radial-gradient(circle at 88% 22%, rgba(215, 210, 255, 0.65) 0%, transparent 45%),
          radial-gradient(circle at 50% 85%, rgba(210, 235, 255, 0.55) 0%, transparent 50%),
          linear-gradient(135deg, #E6EDFB 0%, #EDF3FD 40%, #E2EAF8 70%, #DAE4F6 100%)
        `,
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Warden Protocol Initializing"
    >
      {/* 2-3% Monochrome Film Grain via SVG feTurbulence Data URI */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Subtle vignette using existing background darkened with black overlay at low opacity */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 50% 50%, transparent 60%, rgba(15, 23, 42, 0.05) 100%)',
        }}
      />

      {/* Center Group: Shield Icon, Wordmark, and Slim Bar */}
      <div className="relative z-10 flex flex-col items-center text-center">
        {/* Inline SVG Shield (~28px) drawing outline */}
        <div className="w-8 h-8 mb-4 flex items-center justify-center">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#0F172A"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="overflow-visible"
          >
            <path
              ref={shieldPathRef}
              d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
            />
          </svg>
        </div>

        {/* Small "WARDEN PROTOCOL" Wordmark */}
        <div
          ref={wordmarkRef}
          className="text-sm font-semibold tracking-[0.32em] uppercase text-slate-900 font-sans select-none mb-6"
          style={{ willChange: 'opacity, filter, letter-spacing' }}
        >
          WARDEN PROTOCOL
        </div>

        {/* Slim Loading Bar (240px x 2px, rounded) */}
        <div
          ref={barTrackRef}
          className="relative w-[240px] h-[2px] rounded-full overflow-visible mb-3"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.1)' }}
        >
          {/* Fill using dashboard accent token (#3B82F6) */}
          <div
            ref={barFillRef}
            className="absolute top-0 left-0 h-full rounded-full"
            style={{ backgroundColor: '#3B82F6' }}
          />

          {/* Soft Glow following leading edge */}
          <div
            ref={barGlowRef}
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full pointer-events-none -ml-2"
            style={{
              backgroundColor: '#3B82F6',
              filter: 'blur(4px)',
            }}
          />
        </div>

        {/* Monospace Caption cycling at 40% opacity */}
        <p
          ref={captionRef}
          role="status"
          aria-live="polite"
          className="text-[11px] font-mono tracking-wider select-none h-4"
          style={{ color: 'rgba(15, 23, 42, 0.45)' }}
        >
          {captionText}
        </p>
      </div>
    </div>
  );
};
