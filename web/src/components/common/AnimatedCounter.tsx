import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';

interface AnimatedCounterProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  duration?: number;
  className?: string;
}

export const AnimatedCounter: React.FC<AnimatedCounterProps> = ({
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  duration = 1.2,
  className = '',
}) => {
  const spanRef = useRef<HTMLSpanElement>(null);
  const prevValRef = useRef<number>(0);

  useEffect(() => {
    if (!spanRef.current) return;

    const obj = { val: prevValRef.current };
    const tween = gsap.to(obj, {
      val: value,
      duration,
      ease: 'power3.out',
      onUpdate: () => {
        if (spanRef.current) {
          const formatted = obj.val.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
          });
          spanRef.current.textContent = `${prefix}${formatted}${suffix}`;
        }
      },
    });

    prevValRef.current = value;
    return () => {
      tween.kill();
    };
  }, [value, prefix, suffix, decimals, duration]);

  const initialFormatted = value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <span ref={spanRef} className={className}>
      {prefix}{initialFormatted}{suffix}
    </span>
  );
};
