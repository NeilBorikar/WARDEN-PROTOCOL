import React, { useState, useRef, useEffect } from 'react';
import { Check } from 'lucide-react';

interface HoldToConfirmButtonProps {
  onConfirm: () => void;
  holdDurationMs?: number;
  label?: string;
  className?: string;
  disabled?: boolean;
}

export const HoldToConfirmButton: React.FC<HoldToConfirmButtonProps> = ({
  onConfirm,
  holdDurationMs = 1200,
  label = 'Hold to Authorize',
  className = '',
  disabled = false,
}) => {
  const [holding, setHolding] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const startTimeRef = useRef<number | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const startHold = () => {
    if (disabled) return;
    setHolding(true);
    startTimeRef.current = Date.now();

    const checkProgress = () => {
      if (!startTimeRef.current) return;
      const elapsed = Date.now() - startTimeRef.current;
      const pct = Math.min(100, (elapsed / holdDurationMs) * 100);
      setProgress(pct);

      if (pct >= 100) {
        cancelHold();
        onConfirm();
      } else {
        animFrameRef.current = requestAnimationFrame(checkProgress);
      }
    };

    animFrameRef.current = requestAnimationFrame(checkProgress);
  };

  const cancelHold = () => {
    setHolding(false);
    setProgress(0);
    startTimeRef.current = null;
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  return (
    <button
      type="button"
      onMouseDown={startHold}
      onMouseUp={cancelHold}
      onMouseLeave={cancelHold}
      onTouchStart={startHold}
      onTouchEnd={cancelHold}
      onKeyDown={(e) => {
        if ((e.key === ' ' || e.key === 'Enter') && !holding) {
          e.preventDefault();
          startHold();
        }
      }}
      onKeyUp={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          cancelHold();
        }
      }}
      disabled={disabled}
      className={`relative overflow-hidden nixtio-pill-dark px-5 py-2.5 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer select-none transition-all ${className}`}
      title="Press and hold for 1.2s to sign and authorize"
    >
      {/* Progress fill layer using dashboard accent token at low alpha */}
      <div
        className="absolute inset-0 bg-blue-500/40 pointer-events-none transition-all duration-75"
        style={{
          width: `${progress}%`,
        }}
      />

      <span className="relative z-10 flex items-center gap-1.5">
        <Check size={14} className={holding ? 'scale-110' : ''} />
        <span>{holding ? `Holding... ${Math.round(progress)}%` : label}</span>
      </span>
    </button>
  );
};
