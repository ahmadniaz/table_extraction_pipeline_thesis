/**
 * Canonical document complexity tiers (same as chart `TIER_SEQ` in chartUtils).
 * All DB / API tier strings are normalized at aggregate build time (see `buildDataset.mergeRows`).
 */
export const TIER_ORDER = ['low', 'medium', 'high', 'unconfirmed'] as const;
export type ComplexityTierKey = (typeof TIER_ORDER)[number];

/** Main thesis tiers (LOW / MEDIUM / HIGH) — unconfirmed excluded from per-tier figure tables. */
export const TIER_THREE = ['low', 'medium', 'high'] as const;

/** Maps any raw tier string to a known bucket; unknown values → unconfirmed (never dropped silently). */
export function normalizeComplexityTier(raw: string): ComplexityTierKey {
  const k = raw.trim().toLowerCase();
  return (TIER_ORDER as readonly string[]).includes(k) ? (k as ComplexityTierKey) : 'unconfirmed';
}
