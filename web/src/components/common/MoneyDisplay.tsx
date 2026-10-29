import React from 'react';

interface MoneyDisplayProps {
  amountMinor: number;
  currency?: string;
  className?: string;
  showCurrency?: boolean;
}

export const MoneyDisplay: React.FC<MoneyDisplayProps> = ({
  amountMinor,
  currency = 'USD',
  className = '',
  showCurrency = false,
}) => {
  const dollars = (amountMinor / 100).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <span className={`inline-flex items-baseline font-mono font-bold tabular-nums tracking-tight ${className}`}>
      <span className="text-[0.85em] opacity-80 mr-0.5">$</span>
      <span>{dollars}</span>
      {showCurrency && (
        <span className="text-[0.75em] text-slate-500 dark:text-slate-400 font-sans font-medium ml-1.5 uppercase px-1 py-0.2 rounded bg-slate-200/50 dark:bg-slate-800 border border-slate-300/40 dark:border-white/10">
          {currency}
        </span>
      )}
    </span>
  );
};
