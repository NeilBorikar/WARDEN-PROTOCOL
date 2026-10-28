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
    <span className={`font-mono font-semibold tabular-nums ${className}`}>
      ${dollars}
      {showCurrency && <span className="text-xs text-slate-400 font-normal ml-1">{currency}</span>}
    </span>
  );
};
