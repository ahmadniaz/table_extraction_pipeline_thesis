export type ToolGeneration = 'rule' | 'cv' | 'llm';

export const SCORE_METRICS = [
  'f1_score',
  'teds_score',
  'grits_top',
  'grits_con',
  'grits_loc',
  'precision',
  'recall',
] as const;
export type ScoreMetric = (typeof SCORE_METRICS)[number];

export const SCAN_MODES = ['all', 'digital', 'scanned', 'unknown'] as const;
export type ScanFilter = (typeof SCAN_MODES)[number];

export type ApiScore = {
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  teds_score: number | null;
  grits_top: number | null;
  grits_con: number | null;
  grits_loc: number | null;
} | null;

export type ExtractionTableRow = {
  extraction_result_id: string;
  document_id: string;
  filename: string;
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
  tool_name: string;
  table_index: number;
  processing_time_ms: number | null;
  cost_usd: number | null;
  error_message: string | null;
  failure_reason: string | null;
  is_transient_failure: boolean;
  is_draft: boolean;
  score: ApiScore;
};

export type DocumentMeta = {
  id: string;
  filename: string;
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
  ground_truth_count: number;
};

export type AnalyticsFailureStatus =
  | 'all'
  | 'success'
  | 'failures'
  | 'partial'
  | 'missing_f1'
  | 'unevaluated';

export type OpenSourceFilter = 'all' | 'open' | 'commercial';

export type AggregateMode = 'all' | 'by_tool' | 'by_tier' | 'by_gen' | 'by_carrier' | 'by_file';

/** How null/missing per-(document×tool) metrics enter means; see `aggregationPolicy.ts`. */
export type MetricAggregationPolicy = 'strict' | 'zero_impute_failed';

export type AnalyticsFilterState = {
  /** Default metric for charts (each chart may still offer its own selector). */
  primaryMetric: ScoreMetric;
  metricAggregationPolicy: MetricAggregationPolicy;
  tools: string[];
  /** Empty = all generations */
  generations: ToolGeneration[];
  /** Empty = all tiers (low, medium, high, unconfirmed) */
  tiers: string[];
  documentSearch: string;
  carrier: string;
  failureStatus: AnalyticsFailureStatus;
  openSource: OpenSourceFilter;
  runtimeMin: string;
  runtimeMax: string;
  costMin: string;
  costMax: string;
  pageCountMin: string;
  pageCountMax: string;
  scan: ScanFilter;
  /**
   * Table/group display only: does not change `filterDocumentToolRows` or chart row sets — the raw
   * table groups rows in the matrix explorer for easier reading.
   */
  aggregateMode: AggregateMode;
};

export const defaultAnalyticsFilters: AnalyticsFilterState = {
  primaryMetric: 'f1_score',
  metricAggregationPolicy: 'strict',
  tools: [],
  generations: [],
  tiers: [],
  documentSearch: '',
  carrier: 'all',
  failureStatus: 'all',
  openSource: 'all',
  runtimeMin: '',
  runtimeMax: '',
  costMin: '',
  costMax: '',
  pageCountMin: '',
  pageCountMax: '',
  scan: 'all',
  aggregateMode: 'all',
};

/**
 * One row per (document × tool): aggregated from table-level extractions.
 * Used for charts and filters. Not every (doc, tool) exists if no extraction;
 * builder fills with synthetic rows for unevaluated slots when needed.
 */
export type DocumentToolAggregate = {
  document_id: string;
  filename: string;
  /** Normalised: low | medium | high | unconfirmed */
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
  tool_name: string;
  generation: ToolGeneration;
  /** Parsed from filename; used when DB has no carrier. */
  carrier: string;
  has_extraction: boolean;
  /** At least one extraction row. */
  table_rows: number;
  /** Rows with a score object. */
  scored_tables: number;
  /** Per-table mean of metric, then we often mean over tables — stored as metric means. */
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  teds_score: number | null;
  grits_top: number | null;
  grits_con: number | null;
  grits_loc: number | null;
  /** Max across tables, aligned with per-document export. */
  processing_time_ms: number;
  cost_usd_total: number;
  cost_per_page: number | null;
  is_transient_failure: boolean;
  failure_reason: string | null;
  ground_truth_count: number;
  reliability: 'success' | 'partial' | 'complete_failure' | 'missing_f1' | 'unevaluated';
};

export type ClassifyReliability = DocumentToolAggregate['reliability'];
