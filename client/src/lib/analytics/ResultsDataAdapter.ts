/**
 * ResultsDataAdapter (Step 6) — single place describing how API data becomes analytics rows.
 *
 * **Source:** `GET /api/analytics/dataset` (see `server/app/api/analytics.py`):
 * every `extraction_results` row with `documents`, left-joined to `evaluation_scores` (null when
 * a table was not scored).
 *
 * **Normalization:** `buildDocumentToolRows` (buildDataset.ts) groups table-level rows to one
 * `DocumentToolAggregate` per (document × tool) across the seven `ALL_EVAL_TOOLS` slots. Missing
 * extractions are still emitted so failure/reliability views stay complete.
 *
 * **Metrics:** means over scored tables for P/R/F1/TEDS/GriTS; time = max table ms; cost = sum
 * of table costs; `cost_per_page` = total / `page_count` when pages known.
 *
 * **Filtering:** `filterDocumentToolRows` applies UI filters; failure slices use `reliability` on
 * each aggregate (see `mergeRows` / `pickReliability` in buildDataset).
 *
 * **Policy:** `metricValueForRow` in `aggregationPolicy.ts` governs how null metrics enter chart means
 * (strict vs. zero imputation) — see `AnalyticsFilterState['metricAggregationPolicy']`.
 *
 * Re-export the building blocks for charts and exports:
 */
export { metricValueForRow } from '@/lib/analytics/aggregationPolicy';
export {
  buildDocumentToolRows,
  filterDocumentToolRows,
  forAccuracyMetrics,
  withScores,
  uniqueCarriers,
} from '@/lib/analytics/buildDataset';
export type {
  DocumentToolAggregate,
  ExtractionTableRow,
  DocumentMeta,
  AnalyticsFilterState,
  MetricAggregationPolicy,
  ScoreMetric,
} from '@/lib/analytics/types';
