/**
 * Step 7 — Auditable metric aggregation for thesis analytics.
 *
 * **Table level (in `buildDataset` / `mergeRows`):** Precision, recall, F1, TEDS, GriTS are
 * averaged only across extraction rows that have a `score` object. `null` in the API means
 * no score; `0.0` is a real scored outcome (e.g. tool produced empty table but was evaluated).
 * This matches the server: `tool_limitation` / `empty_output` → scores stored as 0.0.
 *
 * **Document×tool level (here):** We combine table-level means into one row per (document, tool).
 * `reliability` classifies the run: `unevaluated` (no rows), `missing_f1` (no scores),
 * `complete_failure` (transient already handled), `partial`, `success`.
 *
 * **Policies:**
 * - `strict` (default, thesis): Tool/document averages use only rows where the chosen metric
 *   is a real number. Transient API failures are never averaged in. `null` aggregate = omitted.
 * - `zero_impute_failed`: Sensitivity analysis — (document×tool) rows with no metric but
 *   `reliability` of `complete_failure` or `missing_f1` (and had extraction) count as `0` in
 *   means. `partial` with missing metric also imputes 0. Still excludes `unevaluated` and
 *   `is_transient_failure` from means (those are not “failed extraction quality” in the same sense).
 */
import type { DocumentToolAggregate, MetricAggregationPolicy, ScoreMetric } from '@/lib/analytics/types';

/**
 * Single numeric value for charts/summary for one `DocumentToolAggregate` and metric column.
 * Returns `null` when this row should not contribute to a mean (policy-dependent).
 */
export function metricValueForRow(
  row: DocumentToolAggregate,
  m: ScoreMetric,
  policy: MetricAggregationPolicy
): number | null {
  if (row.is_transient_failure) return null;

  const raw = row[m];
  if (raw != null && !Number.isNaN(raw)) {
    return raw;
  }

  if (policy === 'strict') {
    return null;
  }

  if (!row.has_extraction) {
    return null;
  }

  if (row.reliability === 'unevaluated') {
    return null;
  }

  if (row.reliability === 'complete_failure' || row.reliability === 'missing_f1') {
    return 0;
  }

  if (row.reliability === 'partial') {
    return 0;
  }

  if (row.reliability === 'success') {
    return null;
  }

  return null;
}
