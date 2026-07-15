import type { DocumentToolAggregate, ScoreMetric } from '@/lib/analytics/types';

export function meanSafe(nums: (number | null | undefined)[]): number | null {
  const a = nums.filter((x): x is number => x != null && !Number.isNaN(x));
  if (a.length === 0) return null;
  return a.reduce((s, n) => s + n, 0) / a.length;
}

export function medianSafe(nums: (number | null | undefined)[]): number | null {
  const a = nums
    .filter((x): x is number => x != null && !Number.isNaN(x))
    .sort((p, q) => p - q);
  if (a.length === 0) return null;
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m]! : (a[m - 1]! + a[m]!) / 2;
}

export function metricOf(row: DocumentToolAggregate, m: ScoreMetric): number | null {
  return row[m];
}

export function quantiles(sorted: number[]): { min: number; q1: number; med: number; q3: number; max: number } {
  if (sorted.length === 0) {
    return { min: 0, q1: 0, med: 0, q3: 0, max: 0 };
  }
  const s = [...sorted].sort((a, b) => a - b);
  const q = (p: number) => s[Math.min(s.length - 1, Math.max(0, Math.round(p * (s.length - 1))))]!;
  return {
    min: s[0]!,
    q1: q(0.25),
    med: q(0.5),
    q3: q(0.75),
    max: s[s.length - 1]!,
  };
}
