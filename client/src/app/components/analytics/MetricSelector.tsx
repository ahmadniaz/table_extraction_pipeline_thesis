'use client';

import { METRIC_LABEL } from '@/lib/analytics/metricLabels';
import { SCORE_METRICS, type ScoreMetric } from '@/lib/analytics/types';
import { cn } from '@/lib/utils';

type Props = {
  value: ScoreMetric;
  onChange: (m: ScoreMetric) => void;
  className?: string;
  id?: string;
  size?: 'sm' | 'md';
  /** @default "Metric" */
  ariaLabel?: string;
};

/**
 * Reusable score dropdown for all thesis metrics (F1, TEDS, GriTS, P/R).
 */
export function MetricSelector({ value, onChange, className, id, size = 'md', ariaLabel = 'Metric' }: Props) {
  return (
    <select
      id={id}
      aria-label={ariaLabel}
      className={cn(
        'rounded border border-slate-200 bg-white text-slate-800 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100',
        size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-sm',
        className
      )}
      value={value}
      onChange={e => onChange(e.target.value as ScoreMetric)}
    >
      {SCORE_METRICS.map(m => (
        <option key={m} value={m}>
          {METRIC_LABEL[m]}
        </option>
      ))}
    </select>
  );
}
