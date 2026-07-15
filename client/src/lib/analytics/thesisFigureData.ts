/**
 * Data builders for the minimal Thesis Figures page. Uses the same
 * `DocumentToolAggregate` rows and strict `metricValueForRow` as the thesis tables.
 */
import { ALL_EVAL_TOOLS } from '@/lib/evaluationTools';
import { OPEN_SOURCE_TOOL_IDS } from '@/lib/analytics/chartTheme';
import { metricValueForRow } from '@/lib/analytics/aggregationPolicy';
import { meanByToolAndTier, lineDataByToolTier, toolLabel, sortTools } from '@/lib/analytics/chartUtils';
import { meanSafe } from '@/lib/analytics/stats';
import { TIER_THREE, normalizeComplexityTier } from '@/lib/analytics/tier';
import type { DocumentToolAggregate, MetricAggregationPolicy } from '@/lib/analytics/types';

export const THESIS_METRIC_POLICY: MetricAggregationPolicy = 'strict';

export function thesisF1ByToolAll(rows: DocumentToolAggregate[]) {
  return ALL_EVAL_TOOLS.map(({ id, label }) => {
    const sub = rows.filter(r => r.tool_name === id);
    const vals = sub
      .map(r => metricValueForRow(r, 'f1_score', THESIS_METRIC_POLICY))
      .filter((v): v is number => v != null);
    return { tool: id, label, value: meanSafe(vals) ?? 0 };
  }).sort((a, b) => b.value - a.value);
}

export function thesisF1ByToolAndThreeTiers(rows: DocumentToolAggregate[]) {
  const byTier = meanByToolAndTier(rows, 'f1_score', THESIS_METRIC_POLICY);
  return byTier.map(row => ({
    tool: row.tool as string,
    LOW: (row as Record<string, number>).low ?? 0,
    MEDIUM: (row as Record<string, number>).medium ?? 0,
    HIGH: (row as Record<string, number>).high ?? 0,
  }));
}

export function thesisF1LineDataThreeTiers(rows: DocumentToolAggregate[]) {
  const full = lineDataByToolTier(rows, 'f1_score', THESIS_METRIC_POLICY);
  return TIER_THREE.map(tk => {
    const row = full.find(d => d.tierKey === tk);
    return row ?? { tier: tk.toUpperCase(), tierKey: tk };
  });
}

export function thesisGriTSGroupedByTool(rows: DocumentToolAggregate[]) {
  return ALL_EVAL_TOOLS.map(({ id, label }) => {
    const sub = rows.filter(r => r.tool_name === id);
    const tVals = sub
      .map(r => metricValueForRow(r, 'grits_top', THESIS_METRIC_POLICY))
      .filter((v): v is number => v != null);
    const cVals = sub
      .map(r => metricValueForRow(r, 'grits_con', THESIS_METRIC_POLICY))
      .filter((v): v is number => v != null);
    return {
      tool: id,
      label,
      name: label,
      gritsTop: meanSafe(tVals) ?? 0,
      gritsCon: meanSafe(cVals) ?? 0,
    };
  });
}

type ScatterP = { x: number; y: number; name: string; toolId: string };

export function thesisCostF1Points(rows: DocumentToolAggregate[], includeOpenSource: boolean): ScatterP[] {
  const out: ScatterP[] = [];
  for (const tid of ALL_EVAL_TOOLS.map(t => t.id)) {
    if (!includeOpenSource && OPEN_SOURCE_TOOL_IDS.has(tid)) continue;
    const sub = rows.filter(r => r.tool_name === tid);
    const xs = sub
      .map(r => r.cost_per_page)
      .filter((v): v is number => v != null && !Number.isNaN(v));
    let x: number | null;
    if (includeOpenSource && OPEN_SOURCE_TOOL_IDS.has(tid)) {
      x = 0;
    } else {
      x = meanSafe(xs);
    }
    const ys = sub
      .map(r => metricValueForRow(r, 'f1_score', THESIS_METRIC_POLICY))
      .filter((v): v is number => v != null);
    const y = meanSafe(ys);
    if (x == null || y == null) continue;
    out.push({ x, y, name: toolLabel(tid), toolId: tid });
  }
  return out;
}

export function thesisRuntimeF1Points(rows: DocumentToolAggregate[]): ScatterP[] {
  const out: ScatterP[] = [];
  for (const tid of ALL_EVAL_TOOLS.map(t => t.id)) {
    const sub = rows.filter(r => r.tool_name === tid);
    const xs = sub.map(r => r.processing_time_ms).filter((v): v is number => v != null && !Number.isNaN(v));
    const x = meanSafe(xs);
    const ys = sub
      .map(r => metricValueForRow(r, 'f1_score', THESIS_METRIC_POLICY))
      .filter((v): v is number => v != null);
    const y = meanSafe(ys);
    if (x == null || y == null) continue;
    out.push({ x, y, name: toolLabel(tid), toolId: tid });
  }
  return out;
}

export function thesisFailureStackByTool(rows: DocumentToolAggregate[]) {
  const tools = sortTools(ALL_EVAL_TOOLS.map(t => t.id));
  return tools.map(tid => {
    const r = rows.filter(x => x.tool_name === tid);
    let success = 0;
    let structural = 0;
    let partialOrMissing = 0;
    for (const row of r) {
      if (row.reliability === 'success') {
        success++;
      } else if (row.reliability === 'complete_failure') {
        structural++;
      } else {
        partialOrMissing++;
      }
    }
    return {
      tool: toolLabel(tid),
      toolId: tid,
      successful: success,
      structuralFailure: structural,
      partialOrMissingF1: partialOrMissing,
    };
  });
}

export function thesisCostByTierCommercial(rows: DocumentToolAggregate[]) {
  const commercialIds = ALL_EVAL_TOOLS.map(t => t.id).filter(t => !OPEN_SOURCE_TOOL_IDS.has(t));
  const by: Record<string, { low: number[]; medium: number[]; high: number[] }> = {};
  for (const tid of commercialIds) {
    by[tid] = { low: [], medium: [], high: [] };
  }
  for (const r of rows) {
    if (OPEN_SOURCE_TOOL_IDS.has(r.tool_name)) continue;
    const v = r.cost_per_page;
    if (v == null || Number.isNaN(v)) continue;
    const tr = normalizeComplexityTier(r.complexity_tier);
    if (tr !== 'low' && tr !== 'medium' && tr !== 'high') continue;
    by[r.tool_name]![tr].push(v);
  }
  return commercialIds.map(tid => ({
    tool: toolLabel(tid),
    toolId: tid,
    LOW: meanSafe(by[tid]!.low) ?? 0,
    MEDIUM: meanSafe(by[tid]!.medium) ?? 0,
    HIGH: meanSafe(by[tid]!.high) ?? 0,
  }));
}
