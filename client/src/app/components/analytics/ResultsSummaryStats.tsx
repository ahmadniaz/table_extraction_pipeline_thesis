'use client';

import { cn } from '@/lib/utils';

export type ResultsSummary = {
  bestF1: string;
  fastest: string;
  cheapest: string;
  bestRel: string;
  corpus: string;
};

type Props = {
  summary: ResultsSummary;
  className?: string;
};

function Stat({ label, value = '—' }: { label: string; value?: string }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-slate-200/90 bg-white px-4 py-3 shadow-sm',
        'dark:border-slate-700 dark:bg-slate-900/40'
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1.5 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  );
}

/** Quick summary cards driven by the same filtered document×tool rows as the charts. */
export function ResultsSummaryStats({ summary, className }: Props) {
  return (
    <div className={cn('grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5', className)}>
      <Stat label="Highest aggregate F1" value={summary.bestF1} />
      <Stat label="Fastest tool (mean time)" value={summary.fastest} />
      <Stat label="Cheapest commercial ($/page)" value={summary.cheapest} />
      <Stat label="Lowest fail + missing F1 count" value={summary.bestRel} />
      <Stat label="Corpus" value={summary.corpus} />
    </div>
  );
}
