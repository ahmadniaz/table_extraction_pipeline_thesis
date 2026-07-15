'use client';

import { useEffect, useMemo, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ALL_EVAL_TOOLS } from '@/lib/evaluationTools';
import { OPEN_SOURCE_TOOL_IDS, TOOL_ID_TO_GENERATION, chartColorForTool, chartColorForTier } from '@/lib/analytics/chartTheme';
import { forAccuracyMetrics } from '@/lib/analytics/buildDataset';
import { metricValueForRow } from '@/lib/analytics/aggregationPolicy';
import { normalizeComplexityTier } from '@/lib/analytics/tier';
import { meanSafe } from '@/lib/analytics/stats';
import { METRIC_LABEL } from '@/lib/analytics/metricLabels';
import { type AnalyticsFilterState, type DocumentToolAggregate, type ScoreMetric, type MetricAggregationPolicy } from '@/lib/analytics/types';
import {
  TIER_SEQ,
  boxDataForMetric,
  failureCountsByTool,
  heatmapToolTier,
  lineDataByToolTier,
  meanByToolAndTier,
  meanMetricByTool,
  medianMetricByTool,
  sortTools,
  toolLabel,
} from '@/lib/analytics/chartUtils';
import { ChartCard } from '@/app/components/analytics/ChartCard';
import { MetricSelector } from '@/app/components/analytics/MetricSelector';

/**
 * Results Analytics — chart inventory (all use `rows` = same `filterDocumentToolRows` output as the table/CSV):
 *
 * - Ranking / tier bars / line / box / structure scatters: metric columns + `metricValueForRow` (see `aggregationPolicy.ts`).
 * - Cost & runtime scatters: X = mean of `cost_per_page` or `processing_time_ms` over doc×tool; Y = selected metric (policy).
 * - Cost/time-by-tier bars: non-metric means per tier bucket (no F1 policy on axis values).
 * - Failure stack: `reliability` counts (policy does not change counts).
 * - Heatmap: failure | missing_f1 | mean of metric in cell.
 *
 * `applied.aggregateMode` is display-only for the raw table, not a row filter.
 */
function ChartDataEmpty({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="flex min-h-[200px] items-center justify-center rounded border border-dashed border-slate-200 bg-slate-50/90 px-4 text-center text-sm text-slate-600 dark:border-slate-600 dark:bg-slate-900/40 dark:text-slate-400"
      role="status"
    >
      {children}
    </div>
  );
}

/** Slightly higher contrast on white (Step 9) without heavy ink. */
const GRID = '#cbd5e1';
const AXIS = '#475569';

/** Step 8 — explicit section order per `analyticsPage.md` (academic flow). */
function VizSectionHeading({ id, title, description }: { id: string; title: string; description: string }) {
  return (
    <div className="space-y-1">
      <h3 id={id} className="scroll-mt-4 text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        {title}
      </h3>
      <p className="max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">{description}</p>
    </div>
  );
}

const REL_COLORS = {
  success: '#22c55e',
  partial: '#eab308',
  complete_failure: '#dc2626',
  missing_f1: '#94a3b8',
  unevaluated: '#cbd5e1',
};

type Props = {
  rows: DocumentToolAggregate[];
  applied: AnalyticsFilterState;
};

function meanCostTimeByToolTier(rows: DocumentToolAggregate[], field: 'cost_per_page' | 'processing_time_ms') {
  const by: Record<string, Record<string, number[]>> = {};
  for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
    by[tid] = { low: [], medium: [], high: [], unconfirmed: [] };
  }
  for (const r of rows) {
    const v = field === 'cost_per_page' ? r.cost_per_page : r.processing_time_ms;
    if (v == null || Number.isNaN(v)) continue;
    const tier = normalizeComplexityTier(r.complexity_tier);
    (by[r.tool_name] ??= { low: [], medium: [], high: [], unconfirmed: [] })[tier].push(v);
  }
  return sortTools(ALL_EVAL_TOOLS.map(x => x.id)).map(tid => {
    const o: Record<string, string | number> = { tool: toolLabel(tid) };
    for (const t of TIER_SEQ) {
      o[t] = meanSafe(by[tid]![t] ?? []) ?? 0;
    }
    return o;
  });
}

function toolAggregateScatter(
  rows: DocumentToolAggregate[],
  xKey: 'cost_per_page' | 'processing_time_ms',
  yMetric: ScoreMetric,
  includeZeroCost: boolean,
  commercialOnly: boolean,
  policy: MetricAggregationPolicy
) {
  const out: { name: string; x: number; y: number; toolId: string; gen: string }[] = [];
  for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
    if (commercialOnly && OPEN_SOURCE_TOOL_IDS.has(tid)) continue;
    const sub = rows.filter(r => r.tool_name === tid);
    const xs = sub
      .map(r => (xKey === 'cost_per_page' ? r.cost_per_page : r.processing_time_ms))
      .filter((v): v is number => v != null && !Number.isNaN(v));
    const ys = sub
      .map(r => metricValueForRow(r, yMetric, policy))
      .filter((v): v is number => v != null);
    const x = meanSafe(xs);
    const y = meanSafe(ys);
    if (x == null || y == null) continue;
    if (!includeZeroCost && xKey === 'cost_per_page' && x <= 0) continue;
    out.push({ name: toolLabel(tid), x, y, toolId: tid, gen: TOOL_ID_TO_GENERATION[tid] ?? 'llm' });
  }
  return out;
}

function structureScatter(
  rows: DocumentToolAggregate[],
  mode: 'grits' | 'teds_f1',
  gran: 'tool' | 'tool_tier',
  policy: MetricAggregationPolicy
) {
  const points: { x: number; y: number; name: string; toolId: string; gen: string }[] = [];
  const xMetric: ScoreMetric = mode === 'grits' ? 'grits_top' : 'teds_score';
  const yMetric: ScoreMetric = mode === 'grits' ? 'grits_con' : 'f1_score';
  if (gran === 'tool') {
    for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
      const sub = forAccuracyMetrics(rows.filter(r => r.tool_name === tid), xMetric, policy);
      if (!sub.length) continue;
      const x = meanSafe(sub.map(r => metricValueForRow(r, xMetric, policy))) ?? 0;
      const y = meanSafe(sub.map(r => metricValueForRow(r, yMetric, policy))) ?? 0;
      points.push({ x, y, name: toolLabel(tid), toolId: tid, gen: TOOL_ID_TO_GENERATION[tid] ?? 'llm' });
    }
  } else {
    for (const tid of ALL_EVAL_TOOLS.map(x => x.id)) {
      for (const tier of TIER_SEQ) {
        const sub = forAccuracyMetrics(
          rows.filter(
            r => r.tool_name === tid && normalizeComplexityTier(r.complexity_tier) === tier
          ),
          xMetric,
          policy
        );
        if (!sub.length) continue;
        const x = meanSafe(sub.map(r => metricValueForRow(r, xMetric, policy))) ?? 0;
        const y = meanSafe(sub.map(r => metricValueForRow(r, yMetric, policy))) ?? 0;
        points.push({
          x,
          y,
          name: `${toolLabel(tid)} · ${tier}`,
          toolId: tid,
          gen: TOOL_ID_TO_GENERATION[tid] ?? 'llm',
        });
      }
    }
  }
  return points;
}

function DocumentMatrixTable({ rows, mode }: { rows: DocumentToolAggregate[]; mode: AnalyticsFilterState['aggregateMode'] }) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<keyof DocumentToolAggregate | 'cost_per_page'>('filename');
  const [asc, setAsc] = useState(true);

  const displayed = useMemo(() => {
    let r = rows.filter(x => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return x.filename.toLowerCase().includes(q) || x.tool_name.toLowerCase().includes(q);
    });
    r = [...r].sort((a, b) => {
      const va = a[sortKey as keyof DocumentToolAggregate] ?? '';
      const vb = b[sortKey as keyof DocumentToolAggregate] ?? '';
      const c = va < vb ? -1 : va > vb ? 1 : 0;
      return asc ? c : -c;
    });
    if (mode === 'by_tool') {
      const map: Record<string, DocumentToolAggregate[]> = {};
      for (const x of r) (map[x.tool_name] ??= []).push(x);
      return Object.entries(map).flatMap(([tool, xs]) => {
        const first = xs[0]!;
        return [
          {
            ...first,
            filename: `σ ${toolLabel(tool)} (${xs.length} docs)`,
            document_id: '',
            f1_score: meanSafe(xs.map(z => z.f1_score)) ?? null,
            precision: meanSafe(xs.map(z => z.precision)) ?? null,
            recall: meanSafe(xs.map(z => z.recall)) ?? null,
            teds_score: meanSafe(xs.map(z => z.teds_score)) ?? null,
            grits_top: meanSafe(xs.map(z => z.grits_top)) ?? null,
            grits_con: meanSafe(xs.map(z => z.grits_con)) ?? null,
            grits_loc: meanSafe(xs.map(z => z.grits_loc)) ?? null,
            processing_time_ms: meanSafe(xs.map(z => z.processing_time_ms)) ?? 0,
            cost_usd_total: xs.reduce((s, z) => s + z.cost_usd_total, 0),
            cost_per_page: meanSafe(xs.map(z => z.cost_per_page)) ?? null,
          } as DocumentToolAggregate,
        ];
      });
    }
    return r;
  }, [rows, search, sortKey, asc, mode]);

  const head = (k: keyof DocumentToolAggregate | 'cost_per_page', label: string) => (
    <th className="cursor-pointer border-b border-slate-200 px-2 py-2 text-left text-xs font-semibold dark:border-slate-600" onClick={() => {
      if (sortKey === k) setAsc(!asc);
      else { setSortKey(k); setAsc(true); }
    }}>
      {label}
    </th>
  );

  const exportCsv = () => {
    const cols = ['filename', 'carrier', 'complexity_tier', 'tool', 'generation', 'precision', 'recall', 'f1', 'teds', 'grits_top', 'grits_con', 'grits_loc', 'runtime_ms', 'cost_total', 'cost_per_page', 'reliability'];
    const lines = [cols.join(',')];
    for (const r of displayed) {
      lines.push(
        [
          `"${r.filename}"`,
          r.carrier,
          r.complexity_tier,
          r.tool_name,
          r.generation,
          r.precision ?? '',
          r.recall ?? '',
          r.f1_score ?? '',
          r.teds_score ?? '',
          r.grits_top ?? '',
          r.grits_con ?? '',
          r.grits_loc ?? '',
          r.processing_time_ms,
          r.cost_usd_total,
          r.cost_per_page ?? '',
          r.reliability,
        ].join(',')
      );
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'analytics-filtered-export.csv';
    a.click();
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <input
          className="rounded border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
          placeholder="Search filename or tool…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <button type="button" onClick={exportCsv} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white dark:bg-slate-200 dark:text-slate-900">
          Export CSV
        </button>
      </div>
      <div className="max-h-[480px] overflow-auto rounded border border-slate-100 dark:border-slate-700">
        <table className="w-full min-w-[960px] text-left text-xs">
          <thead className="sticky top-0 bg-white dark:bg-slate-900">
            <tr>
              {head('filename', 'File')}
              {head('carrier', 'Carrier')}
              {head('complexity_tier', 'Tier')}
              {head('tool_name', 'Tool')}
              {head('generation', 'Gen')}
              {head('precision', 'P')}
              {head('recall', 'R')}
              {head('f1_score', 'F1')}
              {head('teds_score', 'TEDS')}
              {head('grits_top', 'G-Top')}
              {head('grits_con', 'G-Con')}
              {head('grits_loc', 'G-Loc')}
              {head('processing_time_ms', 'ms')}
              {head('cost_per_page', '$/pg')}
              {head('reliability', 'Status')}
            </tr>
          </thead>
          <tbody>
            {!rows.length ? (
              <tr>
                <td colSpan={16} className="px-2 py-8 text-center text-slate-500">
                  No rows for current filters (or empty database). Reset filters or reload data.
                </td>
              </tr>
            ) : !displayed.length ? (
              <tr>
                <td colSpan={16} className="px-2 py-8 text-center text-slate-500">
                  No rows match the search box.
                </td>
              </tr>
            ) : (
            displayed.map((r, i) => (
              <tr key={`${r.document_id}-${r.tool_name}-${i}`} className="border-t border-slate-100 dark:border-slate-800">
                <td className="px-2 py-1.5 font-mono text-[11px]">{r.filename}</td>
                <td className="px-2 py-1.5">{r.carrier}</td>
                <td className="px-2 py-1.5 capitalize">{r.complexity_tier}</td>
                <td className="px-2 py-1.5">{toolLabel(r.tool_name)}</td>
                <td className="px-2 py-1.5">{r.generation}</td>
                {[r.precision, r.recall, r.f1_score, r.teds_score, r.grits_top, r.grits_con, r.grits_loc].map((v, j) => (
                  <td key={j} className="px-2 py-1.5 tabular-nums">
                    {v != null ? v.toFixed(4) : '—'}
                  </td>
                ))}
                <td className="px-2 py-1.5 tabular-nums">{r.processing_time_ms}</td>
                <td className="px-2 py-1.5 tabular-nums">{r.cost_per_page != null ? r.cost_per_page.toFixed(6) : '—'}</td>
                <td className="px-2 py-1.5">{r.reliability}</td>
              </tr>
            ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AnalyticsVisualizations({ rows, applied }: Props) {
  const pol = applied.metricAggregationPolicy;
  const m0 = applied.primaryMetric;
  const [aggMetric, setAggMetric] = useState<ScoreMetric>(m0);
  const [aggMode, setAggMode] = useState<'mean' | 'median'>('mean');
  const [tierLayout, setTierLayout] = useState<'grouped' | 'stacked'>('grouped');
  const [lineMetric, setLineMetric] = useState<ScoreMetric>(m0);
  const [visibleTools, setVisibleTools] = useState<Set<string>>(() => new Set(ALL_EVAL_TOOLS.map(t => t.id)));
  const [highlight, setHighlight] = useState<string | null>(null);
  const [boxMetric, setBoxMetric] = useState<ScoreMetric>('f1_score');
  const [costAccMetric, setCostAccMetric] = useState<ScoreMetric>('f1_score');
  const [includeZeroCost, setIncludeZeroCost] = useState(true);
  const [rtMetric, setRtMetric] = useState<ScoreMetric>('f1_score');
  const [rtLog, setRtLog] = useState(false);
  const [costTierCommercial, setCostTierCommercial] = useState(true);
  const [timeUnit, setTimeUnit] = useState<'ms' | 's'>('ms');
  const [failMode, setFailMode] = useState<'count' | 'pct'>('count');
  const [hmMode, setHmMode] = useState<'failure' | 'missing_f1' | 'mean_metric'>('failure');
  const [hmMetric, setHmMetric] = useState<ScoreMetric>('f1_score');
  const [structureGran, setStructureGran] = useState<'tool' | 'tool_tier'>('tool');

  useEffect(() => {
    setAggMetric(m0);
    setLineMetric(m0);
  }, [m0]);

  const rankData = useMemo(() => {
    const src = aggMode === 'mean' ? meanMetricByTool(rows, aggMetric, pol) : medianMetricByTool(rows, aggMetric, pol);
    return [...src].filter(d => d.value != null).sort((a, b) => (b.value! as number) - (a.value! as number));
  }, [rows, aggMetric, aggMode, pol]);

  const tierBarData = useMemo(() => meanByToolAndTier(rows, aggMetric, pol), [rows, aggMetric, pol]);
  const lineData = useMemo(() => lineDataByToolTier(rows, lineMetric, pol), [rows, lineMetric, pol]);
  const stackData = useMemo(() => {
    const fc = failureCountsByTool(rows);
    return ALL_EVAL_TOOLS.map(t => t.id).map(tid => ({
      tool: toolLabel(tid),
      success: fc[tid]!.success,
      partial: fc[tid]!.partial,
      complete_failure: fc[tid]!.complete_failure,
      missing_f1: fc[tid]!.missing_f1,
      unevaluated: fc[tid]!.unevaluated,
    }));
  }, [rows]);
  const stackDataPct = useMemo(() => {
    return stackData.map(row => {
      const s = row.success + row.partial + row.complete_failure + row.missing_f1 + row.unevaluated;
      if (!s) return { ...row };
      return {
        tool: row.tool,
        success: (row.success / s) * 100,
        partial: (row.partial / s) * 100,
        complete_failure: (row.complete_failure / s) * 100,
        missing_f1: (row.missing_f1 / s) * 100,
        unevaluated: (row.unevaluated / s) * 100,
      };
    });
  }, [stackData]);

  const costTierData = useMemo(() => {
    const raw = meanCostTimeByToolTier(rows, 'cost_per_page');
    if (!costTierCommercial) return raw;
    return raw.filter(r => {
      const tid = ALL_EVAL_TOOLS.find(t => toolLabel(t.id) === r.tool)?.id;
      return tid && !OPEN_SOURCE_TOOL_IDS.has(tid);
    });
  }, [rows, costTierCommercial]);

  const timeTierData = useMemo(() => {
    const raw = meanCostTimeByToolTier(rows, 'processing_time_ms');
    const f = timeUnit === 's' ? raw.map(r => {
      const o: Record<string, string | number | null> = { tool: r.tool };
      for (const t of TIER_SEQ) o[t] = r[t] != null ? (r[t] as number) / 1000 : null;
      return o;
    }) : raw;
    return f;
  }, [rows, timeUnit]);

  const heatCells = useMemo(
    () => heatmapToolTier(rows, hmMode, hmMode === 'mean_metric' ? hmMetric : 'f1_score', pol),
    [rows, hmMode, hmMetric, pol]
  );

  const boxRows = useMemo(() => boxDataForMetric(rows, boxMetric, pol), [rows, boxMetric, pol]);
  const boxDomain = useMemo(() => {
    if (!boxRows.length) return { min: 0, max: 1 };
    const lo = Math.min(...boxRows.map(b => b.min));
    const hi = Math.max(...boxRows.map(b => b.max));
    const p = (hi - lo) * 0.05 || 0.02;
    return { min: Math.max(0, lo - p), max: Math.min(1, hi + p) || 1 };
  }, [boxRows]);
  const maxHeat = useMemo(() => Math.max(0.0001, ...heatCells.map(h => h.value)), [heatCells]);

  const costScatter = useMemo(
    () => toolAggregateScatter(rows, 'cost_per_page', costAccMetric, includeZeroCost, false, pol),
    [rows, costAccMetric, includeZeroCost, pol]
  );
  const rtScatter = useMemo(
    () => toolAggregateScatter(rows, 'processing_time_ms', rtMetric, true, false, pol),
    [rows, rtMetric, pol]
  );
  const rtScatterPlotted = useMemo(
    () => rtScatter.map(d => ({ ...d, x: rtLog ? Math.log10(Math.max(d.x, 1)) : d.x })),
    [rtScatter, rtLog]
  );
  const gritsPoints = useMemo(() => structureScatter(rows, 'grits', structureGran, pol), [rows, structureGran, pol]);
  const tedsPoints = useMemo(() => structureScatter(rows, 'teds_f1', structureGran, pol), [rows, structureGran, pol]);

  return (
    <div className="space-y-10">
      {rows.length === 0 ? (
        <div
          className="rounded-lg border border-amber-200/90 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100"
          role="status"
        >
          <strong className="font-medium">No data for current filters.</strong> The evaluation dataset has no
          (document×tool) rows in this slice. Reset filters, broaden document search, or load extractions in the
          database. Figures below stay available but will be empty.
        </div>
      ) : null}
      <section className="space-y-4" aria-labelledby="sec-viz-accuracy">
        <VizSectionHeading
          id="sec-viz-accuracy"
          title="Accuracy"
          description="Model performance: overall ranking, scores by document complexity tier, trend from low to high tier, and metric dispersion across document×tool runs."
        />
        <ChartCard
          title="Aggregate accuracy ranking by tool"
          subtitle="Horizontal bars; sort by selected metric."
          exportFileName="aggregate-accuracy-by-tool"
        >
          <div className="mb-3 flex flex-wrap items-center gap-3 text-xs">
            <MetricSelector value={aggMetric} onChange={setAggMetric} size="md" />
            <label className="flex items-center gap-1">
              <input type="radio" checked={aggMode === 'mean'} onChange={() => setAggMode('mean')} />
              Mean
            </label>
            <label className="flex items-center gap-1">
              <input type="radio" checked={aggMode === 'median'} onChange={() => setAggMode('median')} />
              Median
            </label>
          </div>
          {rankData.length === 0 ? (
            <ChartDataEmpty>
              No tools have a value for {METRIC_LABEL[aggMetric]} with the current policy and filters (all excluded or
              non-numeric).
            </ChartDataEmpty>
          ) : (
            <div className="h-[360px] w-full">
              <ResponsiveContainer>
                <BarChart layout="vertical" data={rankData} margin={{ left: 100, right: 24, top: 8, bottom: 8 }}>
                  <CartesianGrid stroke={GRID} horizontal={false} />
                  <XAxis type="number" tick={{ fill: AXIS, fontSize: 11 }} domain={[0, 'auto']} />
                  <YAxis type="category" dataKey="label" width={96} tick={{ fill: AXIS, fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => v?.toFixed(4)} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} label={{ position: 'right', fontSize: 10, fill: AXIS }}>
                    {rankData.map(e => (
                      <Cell key={e.tool} fill={chartColorForTool(e.tool)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Accuracy by complexity tier"
          subtitle="Grouped bars (default) or stacked."
          exportFileName="accuracy-by-complexity-tier"
        >
          <div className="mb-3 flex flex-wrap gap-3 text-xs">
            <MetricSelector value={aggMetric} onChange={setAggMetric} size="md" />
            <label className="flex items-center gap-1">
              <input type="radio" checked={tierLayout === 'grouped'} onChange={() => setTierLayout('grouped')} />
              Grouped
            </label>
            <label className="flex items-center gap-1">
              <input type="radio" checked={tierLayout === 'stacked'} onChange={() => setTierLayout('stacked')} />
              Stacked
            </label>
          </div>
          <div className="h-[380px] w-full">
            <ResponsiveContainer>
              <BarChart data={tierBarData} margin={{ left: 8, right: 8, top: 8, bottom: 40 }}>
                <CartesianGrid stroke={GRID} />
                <XAxis dataKey="tool" tick={{ fill: AXIS, fontSize: 10 }} angle={-25} textAnchor="end" height={56} />
                <YAxis tick={{ fill: AXIS, fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {TIER_SEQ.map(t => (
                  <Bar
                    key={t}
                    dataKey={t}
                    stackId={tierLayout === 'stacked' ? 'a' : undefined}
                    fill={chartColorForTier(t)}
                    name={t.toUpperCase()}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Performance degradation across complexity"
          subtitle="LOW → HIGH; toggle series visibility. Click legend to highlight one tool."
          exportFileName="performance-degradation-complexity"
        >
          <div className="mb-3 flex flex-wrap gap-2 text-xs">
            <MetricSelector value={lineMetric} onChange={setLineMetric} size="md" />
            <span className="text-slate-500">Show tools:</span>
            {ALL_EVAL_TOOLS.map(t => (
              <label key={t.id} className="flex items-center gap-0.5">
                <input
                  type="checkbox"
                  checked={visibleTools.has(t.id)}
                  onChange={() => {
                    setVisibleTools(prev => {
                      const n = new Set(prev);
                      if (n.has(t.id)) n.delete(t.id);
                      else n.add(t.id);
                      return n;
                    });
                  }}
                />
                {t.label}
              </label>
            ))}
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer>
              <LineChart data={lineData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                <CartesianGrid stroke={GRID} />
                <XAxis dataKey="tier" tick={{ fill: AXIS, fontSize: 11 }} />
                <YAxis tick={{ fill: AXIS, fontSize: 11 }} />
                <Tooltip />
                <Legend
                  onClick={(e: unknown) => {
                    const d = (e as { dataKey?: string }).dataKey;
                    if (d) setHighlight(x => (x === d ? null : d));
                  }}
                />
                {ALL_EVAL_TOOLS.map(t => {
                  if (!visibleTools.has(t.id)) return null;
                  const dim = highlight && highlight !== t.id ? 0.2 : 1;
                  return (
                    <Line
                      key={t.id}
                      type="monotone"
                      dataKey={t.id}
                      name={t.label}
                      stroke={chartColorForTool(t.id)}
                      strokeWidth={2}
                      strokeOpacity={dim}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Metric distribution by tool"
          subtitle="Whisker summary (min, Q1, median, Q3, max) over document×tool means."
          exportFileName="metric-distribution-by-tool"
        >
          <div className="mb-2">
            <MetricSelector value={boxMetric} onChange={setBoxMetric} size="sm" />
          </div>
          {boxRows.length === 0 ? (
            <ChartDataEmpty>
              No numeric values for {METRIC_LABEL[boxMetric]} under the current metric policy, or all tools are
              filtered out. Try another metric or a different policy in the filter panel.
            </ChartDataEmpty>
          ) : (
            <div className="space-y-2">
            {boxRows.map(b => {
              const w = 100;
              const { min: bmin, max: bmax } = boxDomain;
              const x = (v: number) => ((v - bmin) / (bmax - bmin || 1)) * w;
              return (
                <div key={b.tool} className="flex items-center gap-2 text-xs">
                  <span className="w-32 shrink-0 text-right text-slate-600">{b.label}</span>
                  <div className="relative h-6 flex-1 rounded border border-slate-200 bg-slate-50 dark:border-slate-600 dark:bg-slate-900">
                    <div
                      className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-slate-400"
                      style={{ left: `${x(b.min)}%`, width: `${Math.max(0, x(b.max) - x(b.min))}%` }}
                    />
                    <div
                      className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-slate-700"
                      style={{ left: `${x(b.q1)}%` }}
                    />
                    <div
                      className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-slate-700"
                      style={{ left: `${x(b.q3)}%` }}
                    />
                    <div
                      className="absolute top-1/2 h-3 w-1 -translate-x-1/2 -translate-y-1/2 bg-slate-900"
                      style={{ left: `${x(b.med)}%` }}
                    />
                  </div>
                  <span className="w-20 shrink-0 text-slate-500">n={b.n}</span>
                </div>
              );
            })}
            </div>
          )}
          {boxRows.length > 0 ? (
          <p className="mt-2 text-xs text-slate-500">
            Whisker: min | Q1 | median (thick) | Q3 | max. Domain: {boxDomain.min.toFixed(2)} – {boxDomain.max.toFixed(2)}.
          </p>
          ) : null}
        </ChartCard>
      </section>

      <section className="space-y-4" aria-labelledby="sec-viz-structure">
        <VizSectionHeading
          id="sec-viz-structure"
          title="Structure and content"
          description="Structural quality versus content quality (GriTS-Top vs GriTS-Con, or TEDS vs F1) on tool or tool×tier aggregates."
        />
        <ChartCard
          title="Structure vs content comparison"
          subtitle="GriTS-Top vs GriTS-Con, or TEDS vs F1. Points: tool (or tool×tier)."
          exportFileName="structure-vs-content"
        >
          <Tabs.Root defaultValue="grits" className="w-full">
            <Tabs.List className="mb-2 flex gap-1 border-b border-slate-200 text-xs">
              <Tabs.Trigger value="grits" className="px-2 py-1 data-[state=active]:border-b-2 data-[state=active]:border-slate-800">
                GriTS-Top vs Con
              </Tabs.Trigger>
              <Tabs.Trigger value="teds" className="px-2 py-1 data-[state=active]:border-b-2 data-[state=active]:border-slate-800">
                TEDS vs F1
              </Tabs.Trigger>
            </Tabs.List>
            <div className="mb-2 text-xs">
              <span className="mr-2 text-slate-500">Points</span>
              <select
                className="rounded border border-slate-200 bg-white px-1 py-0.5"
                value={structureGran}
                onChange={e => setStructureGran(e.target.value as 'tool' | 'tool_tier')}
              >
                <option value="tool">Tool aggregate</option>
                <option value="tool_tier">Tool × tier</option>
              </select>
            </div>
            <Tabs.Content value="grits">
              <ScatterPane
                points={gritsPoints}
                xLabel="GriTS-Top (structure)"
                yLabel="GriTS-Con (content)"
                emptyHint="No tool or tool×tier points with a scored GriTS-Top (x) for this filter set."
              />
            </Tabs.Content>
            <Tabs.Content value="teds">
              <ScatterPane
                points={tedsPoints}
                xLabel="TEDS (structure)"
                yLabel="F1 (content)"
                emptyHint="No tool or tool×tier points with a scored TEDS (x) for this filter set."
              />
            </Tabs.Content>
          </Tabs.Root>
        </ChartCard>
      </section>

      <section className="space-y-4" aria-labelledby="sec-viz-operational">
        <VizSectionHeading
          id="sec-viz-operational"
          title="Operational trade-offs"
          description="Cost and runtime against accuracy, plus cost and processing time by tier and tool."
        />
        <ChartCard
          title="Cost vs accuracy trade-off"
          subtitle="Point = tool. X: mean $/page; Y: same metric and aggregation policy as the filter panel (over filtered doc×tool rows)."
          exportFileName="cost-vs-accuracy"
        >
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            <span>Y:</span>
            <MetricSelector value={costAccMetric} onChange={setCostAccMetric} size="sm" />
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={includeZeroCost} onChange={e => setIncludeZeroCost(e.target.checked)} />
              Include $0
            </label>
          </div>
          {costScatter.length === 0 ? (
            <ChartDataEmpty>
              No tools with both a mean {METRIC_LABEL[costAccMetric]} (Y) and mean cost/page (X) for these filters. Try
              unchecking “Include $0” or switch Y metric.
            </ChartDataEmpty>
          ) : (
            <div className="h-[320px] w-full">
              <ScatterPlot
                data={costScatter}
                yLabel={METRIC_LABEL[costAccMetric]}
                xLabel="Mean cost / page (USD)"
              />
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Runtime vs accuracy"
          subtitle="Mean max table time (ms) per document×tool vs selected metric, with the same aggregation policy as the filters."
          exportFileName="runtime-vs-accuracy"
        >
          <div className="mb-2 flex items-center gap-2 text-xs">
            <span>Y:</span>
            <MetricSelector value={rtMetric} onChange={setRtMetric} size="sm" />
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={rtLog} onChange={e => setRtLog(e.target.checked)} />
              Log time
            </label>
          </div>
          {rtScatter.length === 0 ? (
            <ChartDataEmpty>
              No tools with both mean time and a numeric {METRIC_LABEL[rtMetric]} for these filters.
            </ChartDataEmpty>
          ) : (
            <div className="h-[320px] w-full">
              <ScatterPlot
                data={rtScatterPlotted}
                yLabel={METRIC_LABEL[rtMetric]}
                xLabel={rtLog ? 'log10(ms)' : 'Mean time (ms)'}
              />
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Cost by tier and tool"
          subtitle="Mean cost per page. Toggle hide open-source."
          exportFileName="cost-by-tier-and-tool"
        >
          <div className="mb-2 text-xs">
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={costTierCommercial} onChange={e => setCostTierCommercial(e.target.checked)} />
              Commercial only
            </label>
          </div>
          {costTierData.length === 0 ? (
            <ChartDataEmpty>No commercial tools in this view, or no cost/$. Turn off “Commercial only” to show all tools.</ChartDataEmpty>
          ) : (
            <div className="h-[360px] w-full">
              <ResponsiveContainer>
                <BarChart data={costTierData} margin={{ left: 8, right: 8, bottom: 44, top: 8 }}>
                  <CartesianGrid stroke={GRID} />
                  <XAxis dataKey="tool" tick={{ fontSize: 10, fill: AXIS }} angle={-20} textAnchor="end" height={48} />
                  <YAxis tick={{ fontSize: 11, fill: AXIS }} tickFormatter={v => v.toFixed(4)} />
                  <Tooltip formatter={(v: number) => (typeof v === 'number' ? v.toFixed(6) : v)} />
                  <Legend />
                  {TIER_SEQ.map(t => (
                    <Bar key={t} dataKey={t} fill={chartColorForTier(t)} name={t.toUpperCase()} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Processing time by tier and tool"
          subtitle="Mean max table time per document, by tier."
          exportFileName="processing-time-by-tier-and-tool"
        >
          <div className="mb-2 text-xs">
            <label className="mr-3">
              <input type="radio" className="mr-1" checked={timeUnit === 'ms'} onChange={() => setTimeUnit('ms')} />
              ms
            </label>
            <label>
              <input type="radio" className="mr-1" checked={timeUnit === 's'} onChange={() => setTimeUnit('s')} />
              seconds
            </label>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer>
              <BarChart data={timeTierData} margin={{ left: 8, right: 8, bottom: 44, top: 8 }}>
                <CartesianGrid stroke={GRID} />
                <XAxis dataKey="tool" tick={{ fontSize: 10, fill: AXIS }} angle={-20} textAnchor="end" height={48} />
                <YAxis tick={{ fontSize: 11, fill: AXIS }} />
                <Tooltip />
                <Legend />
                {TIER_SEQ.map(t => (
                  <Bar key={t} dataKey={t} fill={chartColorForTier(t)} name={t.toUpperCase()} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </section>

      <section className="space-y-4" aria-labelledby="sec-viz-reliability">
        <VizSectionHeading
          id="sec-viz-reliability"
          title="Reliability"
          description="Extraction outcome mix by tool, and a tool×tier heatmap (failures, missing F1, or mean score)."
        />
        <ChartCard
          title="Failure and partial extraction analysis"
          subtitle="(Document × tool) pairs by reliability."
          exportFileName="failure-partial-extraction"
        >
          <div className="mb-2 text-xs">
            <label className="mr-2">
              <input type="radio" className="mr-1" checked={failMode === 'count'} onChange={() => setFailMode('count')} />
              Count
            </label>
            <label>
              <input type="radio" className="mr-1" checked={failMode === 'pct'} onChange={() => setFailMode('pct')} />
              %
            </label>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer>
              <BarChart
                data={failMode === 'count' ? stackData : stackDataPct}
                margin={{ left: 8, right: 8, bottom: 36, top: 8 }}
              >
                <CartesianGrid stroke={GRID} />
                <XAxis dataKey="tool" tick={{ fontSize: 10, fill: AXIS }} />
                <YAxis
                  tick={{ fontSize: 11, fill: AXIS }}
                  tickFormatter={v => (typeof v === 'number' && failMode === 'pct' ? `${v.toFixed(0)}%` : v)}
                />
                <Tooltip />
                <Legend />
                <Bar dataKey="success" stackId="a" fill={REL_COLORS.success} name="Success" />
                <Bar dataKey="partial" stackId="a" fill={REL_COLORS.partial} name="Partial" />
                <Bar dataKey="complete_failure" stackId="a" fill={REL_COLORS.complete_failure} name="Failed" />
                <Bar dataKey="missing_f1" stackId="a" fill={REL_COLORS.missing_f1} name="Missing F1" />
                <Bar dataKey="unevaluated" stackId="a" fill={REL_COLORS.unevaluated} name="No extraction" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Tool × complexity heatmap"
          subtitle="Cell value = failure count, missing F1 count, or mean of the selected metric (read the mode control)."
          exportFileName="failure-heatmap-by-tool-tier"
        >
          <div className="mb-2 flex flex-wrap gap-2 text-xs">
            <select
              className="rounded border border-slate-200 bg-white px-1 py-0.5 text-xs dark:border-slate-600 dark:bg-slate-900"
              value={hmMode}
              onChange={e => setHmMode(e.target.value as typeof hmMode)}
            >
              <option value="failure">Failure count</option>
              <option value="missing_f1">Missing F1 count</option>
              <option value="mean_metric">Mean metric</option>
            </select>
            {hmMode === 'mean_metric' ? <MetricSelector value={hmMetric} onChange={setHmMetric} size="sm" /> : null}
          </div>
          <div className="overflow-x-auto">
            <div className="grid min-w-[600px] gap-0.5" style={{ gridTemplateColumns: `100px repeat(${TIER_SEQ.length}, minmax(0,1fr))` }}>
              <div />
              {TIER_SEQ.map(t => (
                <div key={t} className="px-1 text-center text-xs font-medium uppercase text-slate-600">
                  {t}
                </div>
              ))}
              {sortTools(ALL_EVAL_TOOLS.map(t => t.id)).map(tid => (
                <div key={tid} className="contents">
                  <div className="pr-1 text-right text-xs font-medium text-slate-700">{toolLabel(tid)}</div>
                  {TIER_SEQ.map(tier => {
                    const v = heatCells.find(h => h.tool === tid && h.tier === tier)?.value ?? 0;
                    const fillRatio = 0.15 + 0.65 * (v / maxHeat);
                    const bg = `rgba(30, 41, 59, ${fillRatio})`;
                    const textLight = fillRatio > 0.45;
                    return (
                      <div
                        key={tier}
                        className={
                          'flex h-8 items-center justify-center text-[11px] font-medium tabular-nums' +
                          (textLight ? ' text-white' : ' text-slate-900')
                        }
                        style={{ background: bg }}
                        title={`${toolLabel(tid)} ${tier}: ${v}`}
                      >
                        {hmMode === 'mean_metric' ? (v as number).toFixed(3) : v}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </section>

      <section className="space-y-4" aria-labelledby="sec-viz-raw">
        <VizSectionHeading
          id="sec-viz-raw"
          title="Raw results explorer"
          description="Sortable document×tool rows matching the current filters, with in-browser CSV export for validation and thesis tables."
        />
        <ChartCard
          title="Per-document matrix explorer"
          subtitle="One row per document × tool after filters."
          exportFileName="per-document-matrix"
        >
          <DocumentMatrixTable rows={rows} mode={applied.aggregateMode} />
        </ChartCard>
      </section>
    </div>
  );
}

type ScatterPoint = { x: number; y: number; name: string; toolId: string; gen: string };

function ScatterPane({
  points,
  xLabel,
  yLabel,
  emptyHint,
}: {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  emptyHint: string;
}) {
  if (points.length === 0) {
    return <ChartDataEmpty>{emptyHint}</ChartDataEmpty>;
  }
  return (
    <div className="h-[300px] w-full min-h-[300px]">
      <ScatterPlot data={points} xLabel={xLabel} yLabel={yLabel} />
    </div>
  );
}

function ScatterPlot({ data, xLabel, yLabel }: { data: ScatterPoint[]; xLabel: string; yLabel: string }) {
  if (data.length === 0) {
    return <ChartDataEmpty>No points in this view.</ChartDataEmpty>;
  }
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ left: 8, right: 8, top: 8, bottom: 28 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis
          type="number"
          dataKey="x"
          tick={{ fontSize: 10, fill: AXIS }}
          label={{ value: xLabel, position: 'bottom', offset: 0, fontSize: 10, fill: AXIS }}
        />
        <YAxis
          type="number"
          dataKey="y"
          tick={{ fontSize: 10, fill: AXIS }}
          label={{ value: yLabel, angle: -90, position: 'insideLeft', fontSize: 10, fill: AXIS }}
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          content={({ active, payload }) => {
            if (!active || !payload?.[0]) return null;
            const p = payload[0].payload as ScatterPoint;
            return (
              <div className="rounded border border-slate-200 bg-white p-2 text-xs shadow dark:border-slate-600 dark:bg-slate-900">
                <div className="font-medium text-slate-800 dark:text-slate-100">{p.name}</div>
                <div className="tabular-nums text-slate-600">
                  {xLabel}: {p.x.toFixed(4)}; {yLabel}: {p.y.toFixed(4)}
                </div>
              </div>
            );
          }}
        />
        <Scatter name="points" data={data}>
          {data.map((e, i) => (
            <Cell key={i} fill={chartColorForTool(e.toolId)} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
