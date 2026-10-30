import React, { useEffect, useState } from 'react';

interface TTLCountdownRingProps {
  expiresAt: string;
  createdAt: string;
  size?: number;
}

export const TTLCountdownRing: React.FC<TTLCountdownRingProps> = ({
  expiresAt,
  createdAt,
  size = 44,
}) => {
  const [secondsLeft, setSecondsLeft] = useState<number>(0);
  const [totalSeconds, setTotalSeconds] = useState<number>(15 * 60);

  useEffect(() => {
    const start = new Date(createdAt).getTime();
    const expiry = new Date(expiresAt).getTime();
    const durationSec = Math.max(1, Math.round((expiry - start) / 1000));
    setTotalSeconds(durationSec);

    const updateTimer = () => {
      const now = Date.now();
      const diffSec = Math.max(0, Math.round((expiry - now) / 1000));
      setSecondsLeft(diffSec);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [expiresAt, createdAt]);

  const radius = (size - 6) / 2;
  const circumference = 2 * Math.PI * radius;
  const progressRatio = Math.max(0, Math.min(1, secondsLeft / totalSeconds));
  const strokeDashoffset = circumference * (1 - progressRatio);

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;
  const formattedTime = `${mins}:${secs < 10 ? '0' : ''}${secs}`;

  return (
    <div
      className="relative flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
      title={`Single-use TTL: ${formattedTime} remaining before escalation auto-expires`}
    >
      <svg width={size} height={size} className="rotate-[-90deg]">
        {/* Track using text token at low alpha */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(15, 23, 42, 0.1)"
          strokeWidth="3"
        />
        {/* Accent stroke */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#3B82F6"
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s linear' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-[9px] font-mono font-bold text-slate-800 leading-none">
          {formattedTime}
        </span>
        <span className="text-[7px] font-mono text-slate-400 uppercase tracking-tighter">
          TTL
        </span>
      </div>
    </div>
  );
};
