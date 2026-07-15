/**
 * Builds document×tool aggregates from table-level API rows. Table-level means use only
 * rows with a `score` object; `null` metrics are dropped from the inner mean, so `0.0` in
 * the DB (real zero) stays distinct from “no score”. See `aggregationPolicy.ts` for tool-level means.
 */
import { ALL_EVAL_TOOLS } from '@/lib/evaluationTools';
import { TOOL_ID_TO_GENERATION, OPEN_SOURCE_TOOL_IDS } from '@/lib/analytics/chartTheme';
import { inferCarrierFromFilename } from '@/lib/analytics/carrier';
import { normalizeComplexityTier } from '@/lib/analytics/tier';
import { metricValueForRow } from '@/lib/analytics/aggregationPolicy';
import type {
  AnalyticsFilterState,
  DocumentMeta,
  DocumentToolAggregate,
  ExtractionTableRow,
  MetricAggregationPolicy,
  ScoreMetric,
} from '@/lib/analytics/types';

const ALL_TOOL_IDS = ALL_EVAL_TOOLS.map(t => t.id);

function meanMetric(
  get: (s: NonNullable<ExtractionTableRow['score']>) => number | null,
  rows: ExtractionTableRow[]
): number | null {
  const v = rows.filter(r => r.score != null).map(r => get(r.score!));
  return meanOf(v);
}
function meanOf(v: (number | null)[]): number | null {
  const a = v.filter((x): x is number => x != null && !Number.isNaN(x));
  if (!a.length) return null;
  return a.reduce((s, n) => s + n, 0) / a.length;
}

function pickReliability(
  rows: ExtractionTableRow[],
  hasExtraction: boolean,
  gt: number
): DocumentToolAggregate['reliability'] {
  if (!hasExtraction) return 'unevaluated';
  if (rows.some(r => r.is_transient_failure)) return 'complete_failure';
  const scored = rows.filter(r => r.score != null);
  if (scored.length === 0) return 'missing_f1';
  if (scored.length < rows.length) return 'partial';
  if (gt > 0 && rows.length < gt) return 'partial';
  return 'success';
}

/**
 * After grouping table rows, build a single {@link DocumentToolAggregate}.
 */
function mergeRows(
  document: DocumentMeta,
  tool: string,
  rows: ExtractionTableRow[]
): DocumentToolAggregate {
  const hasExtraction = rows.length > 0;
  const fr = hasExtraction ? (rows[0]!.failure_reason ?? null) : null;
  const isTransient = hasExtraction && rows.some(r => r.is_transient_failure);
  const proc = hasExtraction ? Math.max(...rows.map(r => r.processing_time_ms ?? 0), 0) : 0;
  const costTotal = hasExtraction ? rows.reduce((s, r) => s + (r.cost_usd ?? 0), 0) : 0;
  const page = document.page_count;
  const cpp = page && page > 0 ? costTotal / page : null;

  const scoredN = rows.filter(r => r.score != null).length;
  const prec = rows.length ? meanMetric(s => s.precision, rows) : null;
  const rec = rows.length ? meanMetric(s => s.recall, rows) : null;
  const f1 = rows.length ? meanMetric(s => s.f1_score, rows) : null;
  const teds = rows.length ? meanMetric(s => s.teds_score, rows) : null;
  const gtop = rows.length ? meanMetric(s => s.grits_top, rows) : null;
  const gcon = rows.length ? meanMetric(s => s.grits_con, rows) : null;
  const gloc = rows.length ? meanMetric(s => s.grits_loc, rows) : null;

  const rel = pickReliability(rows, hasExtraction, document.ground_truth_count);
  return {
    document_id: document.id,
    filename: document.filename,
    complexity_tier: normalizeComplexityTier(document.complexity_tier),
    page_count: document.page_count,
    is_digital: document.is_digital,
    tool_name: tool,
    generation: TOOL_ID_TO_GENERATION[tool] ?? 'llm',
    carrier: inferCarrierFromFilename(document.filename),
    has_extraction: hasExtraction,
    table_rows: rows.length,
    scored_tables: scoredN,
    precision: prec,
    recall: rec,
    f1_score: f1,
    teds_score: teds,
    grits_top: gtop,
    grits_con: gcon,
    grits_loc: gloc,
    processing_time_ms: proc,
    cost_usd_total: costTotal,
    cost_per_page: cpp,
    is_transient_failure: isTransient,
    failure_reason: fr,
    ground_truth_count: document.ground_truth_count,
    reliability: rel,
  };
}

export function buildDocumentToolRows(
  documents: DocumentMeta[],
  rows: ExtractionTableRow[]
): DocumentToolAggregate[] {
  const byDoc: Record<string, ExtractionTableRow[]> = {};
  for (const r of rows) {
    (byDoc[r.document_id] ??= []).push(r);
  }

  const out: DocumentToolAggregate[] = [];
  for (const d of documents) {
    const docRows = byDoc[d.id] ?? [];
    const byTool: Record<string, ExtractionTableRow[]> = {};
    for (const t of docRows) {
      (byTool[t.tool_name] ??= []).push(t);
    }
    for (const tool of ALL_TOOL_IDS) {
      const tr = (byTool[tool] ?? []).sort((a, b) => a.table_index - b.table_index);
      out.push(mergeRows(d, tool, tr));
    }
  }
  return out;
}

function matchesFilter(row: DocumentToolAggregate, f: AnalyticsFilterState): boolean {
  if (f.tools.length && !f.tools.includes(row.tool_name)) return false;
  if (f.generations.length && !f.generations.includes(row.generation)) return false;
  if (f.tiers.length) {
    const t = row.complexity_tier;
    if (!f.tiers.map(x => x.toLowerCase()).includes(t)) return false;
  }
  if (f.documentSearch.trim()) {
    const q = f.documentSearch.trim().toLowerCase();
    if (!row.filename.toLowerCase().includes(q) && !row.document_id.toLowerCase().includes(q)) return false;
  }
  if (f.carrier !== 'all' && f.carrier !== 'Unknown') {
    if (row.carrier !== f.carrier) return false;
  } else if (f.carrier === 'Unknown' && row.carrier !== 'Unknown') return false;

  if (f.openSource === 'open' && !OPEN_SOURCE_TOOL_IDS.has(row.tool_name)) return false;
  if (f.openSource === 'commercial' && OPEN_SOURCE_TOOL_IDS.has(row.tool_name)) return false;

  const tmin = f.runtimeMin === '' ? null : Number(f.runtimeMin);
  const tmax = f.runtimeMax === '' ? null : Number(f.runtimeMax);
  if (tmin != null && !Number.isNaN(tmin) && row.processing_time_ms < tmin) return false;
  if (tmax != null && !Number.isNaN(tmax) && row.processing_time_ms > tmax) return false;

  const cmin = f.costMin === '' ? null : Number(f.costMin);
  const cmax = f.costMax === '' ? null : Number(f.costMax);
  if (cmin != null && !Number.isNaN(cmin) && (row.cost_per_page == null || row.cost_per_page < cmin)) return false;
  if (cmax != null && !Number.isNaN(cmax) && (row.cost_per_page == null || row.cost_per_page > cmax)) return false;

  const pmin = f.pageCountMin === '' ? null : parseInt(f.pageCountMin, 10);
  const pmax = f.pageCountMax === '' ? null : parseInt(f.pageCountMax, 10);
  const pc = row.page_count;
  if (pmin != null && !Number.isNaN(pmin) && (pc == null || pc < pmin)) return false;
  if (pmax != null && !Number.isNaN(pmax) && (pc == null || pc > pmax)) return false;

  if (f.scan === 'digital' && row.is_digital !== true) return false;
  if (f.scan === 'scanned' && row.is_digital !== false) return false;
  if (f.scan === 'unknown' && row.is_digital != null) return false;

  return true;
}

/** Simpler failure filter pass */
function matchFailureStatus(row: DocumentToolAggregate, s: AnalyticsFilterState['failureStatus']): boolean {
  if (s === 'all') return true;
  if (s === 'success') return row.reliability === 'success';
  if (s === 'partial') return row.reliability === 'partial';
  if (s === 'missing_f1') return row.reliability === 'missing_f1';
  if (s === 'failures') {
    return row.reliability === 'complete_failure' || row.is_transient_failure;
  }
  if (s === 'unevaluated') return row.reliability === 'unevaluated';
  return true;
}

export function filterDocumentToolRows(aggregates: DocumentToolAggregate[], f: AnalyticsFilterState): DocumentToolAggregate[] {
  return aggregates.filter(r => matchesFilter(r, f) && matchFailureStatus(r, f.failureStatus));
}

/** Pairs with at least one table-level score. */
export function withScores(rows: DocumentToolAggregate[]): DocumentToolAggregate[] {
  return rows.filter(r => r.scored_tables > 0);
}

/**
 * Rows that contribute a numeric value for metric `m` under the given aggregation policy
 * (see {@link metricValueForRow}).
 */
export function forAccuracyMetrics(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
): DocumentToolAggregate[] {
  return rows.filter(r => metricValueForRow(r, m, policy) != null);
}

export function uniqueCarriers(rows: DocumentToolAggregate[]): string[] {
  return [...new Set(rows.map(r => r.carrier))].sort((a, b) => a.localeCompare(b));
}
