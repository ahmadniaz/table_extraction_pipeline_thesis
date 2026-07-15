/**
 * Central aggregations for analytics charts. Metric-based series use
 * `metricValueForRow` (see `aggregationPolicy.ts`); operational series use raw
 * `cost_per_page` and `processing_time_ms` on each `DocumentToolAggregate` (not policy-gated).
 * Failure/heatmap “failure” and “missing_f1” cells count `reliability` and flags, not metric policy.
 */
import { ALL_EVAL_TOOLS } from '@/lib/evaluationTools';
import { forAccuracyMetrics, withScores } from '@/lib/analytics/buildDataset';
import { metricValueForRow } from '@/lib/analytics/aggregationPolicy';
import { normalizeComplexityTier, TIER_ORDER } from '@/lib/analytics/tier';
import { meanSafe, medianSafe, quantiles } from '@/lib/analytics/stats';
import type { DocumentToolAggregate, MetricAggregationPolicy, ScoreMetric } from '@/lib/analytics/types';

/** Alias for `TIER_ORDER` — kept for `AnalyticsVisualizations` imports. */
const TIER_SEQ = TIER_ORDER;

export function toolLabel(id: string): string {
  return ALL_EVAL_TOOLS.find(t => t.id === id)?.label ?? id;
}

export function sortTools(tools: string[]): string[] {
  const order: string[] = ALL_EVAL_TOOLS.map(t => t.id);
  return [...tools].sort((a, b) => order.indexOf(a) - order.indexOf(b));
}

/** Mean metric per tool (each row = one document×tool mean). */
export function meanMetricByTool(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  const by: Record<string, number[]> = {};
  for (const t of ALL_EVAL_TOOLS.map(x => x.id)) by[t] = [];
  for (const r of rows) {
    const v = metricValueForRow(r, m, policy);
    if (v == null) continue;
    (by[r.tool_name] ??= []).push(v);
  }
  return sortTools(Object.keys(by)).map(tid => ({
    tool: tid,
    label: toolLabel(tid),
    value: meanSafe(by[tid] ?? []),
  }));
}

export function medianMetricByTool(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  const by: Record<string, number[]> = {};
  for (const t of ALL_EVAL_TOOLS.map(x => x.id)) by[t] = [];
  for (const r of rows) {
    const v = metricValueForRow(r, m, policy);
    if (v == null) continue;
    (by[r.tool_name] ??= []).push(v);
  }
  return sortTools(Object.keys(by)).map(tid => ({
    tool: tid,
    label: toolLabel(tid),
    value: medianSafe(by[tid] ?? []),
  }));
}

export function meanByToolAndTier(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  const by: Record<string, Record<string, number[]>> = {};
  for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
    by[tid] = { low: [], medium: [], high: [], unconfirmed: [] };
  }
  for (const r of rows) {
    const v = metricValueForRow(r, m, policy);
    if (v == null) continue;
    const tier = normalizeComplexityTier(r.complexity_tier);
    (by[r.tool_name] ??= { low: [], medium: [], high: [], unconfirmed: [] })[tier].push(v);
  }
  return sortTools(ALL_EVAL_TOOLS.map(x => x.id)).map(tid => {
    const o: Record<string, string | number> = { tool: toolLabel(tid) };
    for (const t of TIER_ORDER) {
      o[t] = meanSafe(by[tid]![t] ?? []) ?? 0;
    }
    return o;
  });
}

export function lineDataByToolTier(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  const byTool: Record<string, Record<string, number[]>> = {};
  for (const r of rows) {
    const v = metricValueForRow(r, m, policy);
    if (v == null) continue;
    const tier = normalizeComplexityTier(r.complexity_tier);
    (byTool[r.tool_name] ??= { low: [], medium: [], high: [], unconfirmed: [] })[tier].push(v);
  }
  const out: Record<string, string | number | null | undefined>[] = [];
  for (const tier of TIER_ORDER) {
    const row: Record<string, string | number | null | undefined> = { tier: tier.toUpperCase(), tierKey: tier };
    for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
      const vs = byTool[tid]?.[tier] ?? [];
      row[tid] = meanSafe(vs);
    }
    out.push(row);
  }
  return out;
}

export function aggregateToolPoint(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  return meanMetricByTool(rows, m, policy).map(x => ({ ...x, name: x.label }));
}

export function f1ByToolPerDocument(rows: DocumentToolAggregate[], tool: string) {
  const v = rows.filter(r => r.tool_name === tool).map(r => r.f1_score).filter((x): x is number => x != null);
  return v;
}

export function boxDataForMetric(
  rows: DocumentToolAggregate[],
  m: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  return sortTools(ALL_EVAL_TOOLS.map(t => t.id))
    .map(tid => {
      const vals = rows
        .filter(r => r.tool_name === tid)
        .map(r => metricValueForRow(r, m, policy))
        .filter((x): x is number => x != null);
      return { tool: tid, label: toolLabel(tid), n: vals.length, ...quantiles(vals) };
    })
    .filter(b => b.n > 0);
}

export function failureCountsByTool(rows: DocumentToolAggregate[]) {
  const rels: DocumentToolAggregate['reliability'][] = [
    'success',
    'partial',
    'complete_failure',
    'missing_f1',
    'unevaluated',
  ];
  const byTool: Record<string, Record<string, number>> = {};
  for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
    byTool[tid] = Object.fromEntries(rels.map(r => [r, 0])) as Record<string, number>;
  }
  for (const r of rows) {
    const t = byTool[r.tool_name];
    if (t) t[r.reliability] = (t[r.reliability] ?? 0) + 1;
  }
  return byTool;
}

export function heatmapToolTier(
  rows: DocumentToolAggregate[],
  mode: 'failure' | 'missing_f1' | 'mean_metric',
  metric: ScoreMetric,
  policy: MetricAggregationPolicy = 'strict'
) {
  const tools = sortTools(ALL_EVAL_TOOLS.map(x => x.id));
  const out: { tool: string; toolLabel: string; tier: string; value: number }[] = [];
  for (const tid of tools) {
    for (const tier of TIER_ORDER) {
      const sub = rows.filter(
        r => r.tool_name === tid && normalizeComplexityTier(r.complexity_tier) === tier
      );
      let v = 0;
      if (mode === 'failure') v = sub.filter(s => s.reliability === 'complete_failure' || s.is_transient_failure).length;
      else if (mode === 'missing_f1') v = sub.filter(s => s.reliability === 'missing_f1').length;
      else {
        v = meanSafe(sub.map(s => metricValueForRow(s, metric, policy)).filter((x): x is number => x != null)) ?? 0;
      }
      out.push({ tool: tid, toolLabel: toolLabel(tid), tier, value: v });
    }
  }
  return out;
}

export { TIER_ORDER, TIER_SEQ, normalizeComplexityTier };
export { withScores, forAccuracyMetrics };
