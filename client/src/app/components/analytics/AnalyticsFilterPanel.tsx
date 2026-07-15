'use client';

import { useMemo } from 'react';
import { ALL_EVAL_TOOLS } from '@/lib/evaluationTools';
import { uniqueCarriers } from '@/lib/analytics/buildDataset';
import type {
  AggregateMode,
  AnalyticsFilterState,
  DocumentToolAggregate,
  OpenSourceFilter,
  ScoreMetric,
  ToolGeneration,
} from '@/lib/analytics/types';
import { SCORE_METRICS, type ScanFilter } from '@/lib/analytics/types';
import { METRIC_LABEL } from '@/lib/analytics/metricLabels';
import { cn } from '@/lib/utils';

const GEN: { id: ToolGeneration; label: string }[] = [
  { id: 'rule', label: 'Rule-based' },
  { id: 'cv', label: 'Computer Vision' },
  { id: 'llm', label: 'LLM' },
];

const TIER_OPTIONS = ['low', 'medium', 'high', 'unconfirmed'] as const;

const FAILURE_OPTIONS: { v: AnalyticsFilterState['failureStatus']; label: string }[] = [
  { v: 'all', label: 'All' },
  { v: 'success', label: 'Successful only' },
  { v: 'failures', label: 'Failures / transient' },
  { v: 'partial', label: 'Partial extractions' },
  { v: 'missing_f1', label: 'Missing F1 only' },
  { v: 'unevaluated', label: 'No extraction' },
];

const OS_OPTIONS: { v: OpenSourceFilter; label: string }[] = [
  { v: 'all', label: 'All' },
  { v: 'open', label: 'Open-source' },
  { v: 'commercial', label: 'Commercial' },
];

const SCAN: { v: ScanFilter; label: string }[] = [
  { v: 'all', label: 'All' },
  { v: 'digital', label: 'Digital' },
  { v: 'scanned', label: 'Scanned' },
  { v: 'unknown', label: 'Unknown' },
];

const AGG: { v: AggregateMode; label: string }[] = [
  { v: 'all', label: 'All documents' },
  { v: 'by_tool', label: 'Group by tool' },
  { v: 'by_tier', label: 'Group by tier' },
  { v: 'by_gen', label: 'Group by generation' },
  { v: 'by_carrier', label: 'Group by carrier' },
  { v: 'by_file', label: 'Group by file' },
];

type Props = {
  draft: AnalyticsFilterState;
  applied: AnalyticsFilterState;
  setDraft: (f: AnalyticsFilterState | ((p: AnalyticsFilterState) => AnalyticsFilterState)) => void;
  onApply: () => void;
  onReset: () => void;
  allRowsForCarriers: DocumentToolAggregate[];
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

function FilterChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200">
      {children}
    </span>
  );
}

export function buildAppliedChips(f: AnalyticsFilterState): { key: string; text: string }[] {
  const c: { key: string; text: string }[] = [];
  if (f.tools.length) c.push({ key: 't', text: `Tools: ${f.tools.join(', ')}` });
  if (f.generations.length) c.push({ key: 'g', text: `Gen: ${f.generations.join(', ')}` });
  if (f.tiers.length) c.push({ key: 'ti', text: `Tiers: ${f.tiers.join(', ')}` });
  if (f.documentSearch.trim()) c.push({ key: 'd', text: `Search: “${f.documentSearch.trim()}”` });
  if (f.carrier !== 'all') c.push({ key: 'c', text: `Carrier: ${f.carrier}` });
  if (f.failureStatus !== 'all') c.push({ key: 'f', text: `Status: ${f.failureStatus}` });
  if (f.openSource !== 'all') c.push({ key: 'o', text: f.openSource });
  if (f.runtimeMin || f.runtimeMax) c.push({ key: 'rt', text: `Time ms: ${f.runtimeMin || '…'}-${f.runtimeMax || '…'}` });
  if (f.costMin || f.costMax) c.push({ key: '$', text: `Cost/pp: ${f.costMin || '…'}-${f.costMax || '…'}` });
  if (f.pageCountMin || f.pageCountMax) c.push({ key: 'p', text: `Pages: ${f.pageCountMin || '…'}-${f.pageCountMax || '…'}` });
  if (f.scan !== 'all') c.push({ key: 's', text: `Scan: ${f.scan}` });
  if (f.aggregateMode !== 'all') c.push({ key: 'a', text: f.aggregateMode });
  if (f.metricAggregationPolicy === 'zero_impute_failed') {
    c.push({ key: 'map', text: 'Metric means: zero-impute (failed / missing as 0)' });
  }
  return c;
}

export function AnalyticsFilterPanel({ draft, applied, setDraft, onApply, onReset, allRowsForCarriers, collapsed, onToggleCollapsed }: Props) {
  const carriers = useMemo(() => ['all', ...uniqueCarriers(allRowsForCarriers)], [allRowsForCarriers]);
  const appliedChips = useMemo(() => buildAppliedChips(applied), [applied]);

  if (collapsed) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 shadow-sm dark:border-slate-600 dark:bg-slate-900"
        >
          Show filters
        </button>
        {appliedChips.length ? (
          <div className="flex flex-wrap gap-1.5">
            {appliedChips.map(x => (
              <FilterChip key={x.key + x.text}>{x.text}</FilterChip>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  const set = (patch: Partial<AnalyticsFilterState>) => setDraft(p => ({ ...p, ...patch }));
  const toggleIn = (arr: string[], v: string) => (arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v]);
  const toggleGen = (g: ToolGeneration) => set({ generations: toggleIn(draft.generations, g) as ToolGeneration[] });
  const toggleTier = (t: string) => set({ tiers: toggleIn(draft.tiers, t) });
  const toggleTool = (id: string) => set({ tools: toggleIn(draft.tools, id) });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300"
        >
          Hide filters
        </button>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onReset}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm dark:border-slate-600 dark:bg-slate-900"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={onApply}
            className="rounded-md bg-slate-800 px-3 py-1.5 text-sm font-medium text-white shadow-sm dark:bg-slate-200 dark:text-slate-900"
          >
            Apply filters
          </button>
        </div>
      </div>

      <div className="grid gap-4 rounded-lg border border-slate-200/90 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900/40 sm:grid-cols-2 lg:grid-cols-3">
        <label className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium uppercase text-slate-500">Default metric (charts)</span>
          <select
            className="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={draft.primaryMetric}
            onChange={e => set({ primaryMetric: e.target.value as ScoreMetric })}
          >
            {SCORE_METRICS.map(m => (
              <option key={m} value={m}>
                {METRIC_LABEL[m]}
              </option>
            ))}
          </select>
        </label>

        <div className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium uppercase text-slate-500">Metric aggregation (means &amp; medians on charts)</span>
          <p className="text-[11px] leading-snug text-slate-500">
            Strict: only (document×tool) rows with a real metric value. Zero-impute: sensitivity analysis — treat failed
            or missing-metric extractions as 0 in tool-level means; transient runs stay excluded.
          </p>
          <div className="flex flex-col gap-1.5 sm:flex-row sm:flex-wrap sm:gap-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="metric-aggregation"
                className="border-slate-300"
                checked={draft.metricAggregationPolicy === 'strict'}
                onChange={() => set({ metricAggregationPolicy: 'strict' })}
              />
              Strict (default)
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="metric-aggregation"
                className="border-slate-300"
                checked={draft.metricAggregationPolicy === 'zero_impute_failed'}
                onChange={() => set({ metricAggregationPolicy: 'zero_impute_failed' })}
              />
              Zero impute
            </label>
          </div>
        </div>

        <div className="sm:col-span-2 lg:col-span-3">
          <span className="text-xs font-medium uppercase text-slate-500">Tools (multi)</span>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {ALL_EVAL_TOOLS.map(t => (
              <label key={t.id} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={draft.tools.includes(t.id)}
                  onChange={() => toggleTool(t.id)}
                  className="rounded border-slate-300"
                />
                {t.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <span className="text-xs font-medium uppercase text-slate-500">Generation</span>
          <div className="mt-1.5 flex flex-col gap-1.5">
            {GEN.map(g => (
              <label key={g.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={draft.generations.includes(g.id)}
                  onChange={() => toggleGen(g.id)}
                />
                {g.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <span className="text-xs font-medium uppercase text-slate-500">Complexity tier</span>
          <div className="mt-1.5 flex flex-col gap-1.5">
            {TIER_OPTIONS.map(t => (
              <label key={t} className="flex items-center gap-2 text-sm capitalize">
                <input type="checkbox" checked={draft.tiers.includes(t)} onChange={() => toggleTier(t)} />
                {t}
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <span className="text-xs font-medium uppercase text-slate-500">Document / filename</span>
          <input
            type="search"
            className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            placeholder="Substring of filename or UUID…"
            value={draft.documentSearch}
            onChange={e => set({ documentSearch: e.target.value })}
          />
        </div>

        <div className="space-y-1.5">
          <span className="text-xs font-medium uppercase text-slate-500">Carrier (inferred)</span>
          <select
            className="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={draft.carrier}
            onChange={e => set({ carrier: e.target.value })}
          >
            {carriers.map(c => (
              <option key={c} value={c}>
                {c === 'all' ? 'All' : c}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <span className="text-xs font-medium uppercase text-slate-500">Extraction / score status</span>
          <select
            className="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={draft.failureStatus}
            onChange={e => set({ failureStatus: e.target.value as typeof draft.failureStatus })}
          >
            {FAILURE_OPTIONS.map(o => (
              <option key={o.v} value={o.v}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <span className="text-xs font-medium uppercase text-slate-500">Open vs commercial</span>
          <select
            className="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={draft.openSource}
            onChange={e => set({ openSource: e.target.value as typeof draft.openSource })}
          >
            {OS_OPTIONS.map(o => (
              <option key={o.v} value={o.v}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium uppercase text-slate-500">Runtime (ms) range</span>
          <div className="flex gap-2">
            <input
              className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              inputMode="numeric"
              placeholder="min"
              value={draft.runtimeMin}
              onChange={e => set({ runtimeMin: e.target.value })}
            />
            <input
              className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              inputMode="numeric"
              placeholder="max"
              value={draft.runtimeMax}
              onChange={e => set({ runtimeMax: e.target.value })}
            />
          </div>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium uppercase text-slate-500">Cost per page (USD) range</span>
          <div className="flex gap-2">
            <input
              className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              inputMode="decimal"
              placeholder="min"
              value={draft.costMin}
              onChange={e => set({ costMin: e.target.value })}
            />
            <input
              className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              inputMode="decimal"
              placeholder="max"
              value={draft.costMax}
              onChange={e => set({ costMax: e.target.value })}
            />
          </div>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium uppercase text-slate-500">Page count range</span>
          <div className="flex gap-2">
            <input
              className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              inputMode="numeric"
              placeholder="min"
              value={draft.pageCountMin}
              onChange={e => set({ pageCountMin: e.target.value })}
            />
            <input
              className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              inputMode="numeric"
              placeholder="max"
              value={draft.pageCountMax}
              onChange={e => set({ pageCountMax: e.target.value })}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <span className="text-xs font-medium uppercase text-slate-500">Scan / digital</span>
          <select
            className="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={draft.scan}
            onChange={e => set({ scan: e.target.value as ScanFilter })}
          >
            {SCAN.map(s => (
              <option key={s.v} value={s.v}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium uppercase text-slate-500">Aggregate / explorer mode</span>
          <select
            className="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={draft.aggregateMode}
            onChange={e => set({ aggregateMode: e.target.value as typeof draft.aggregateMode })}
          >
            {AGG.map(a => (
              <option key={a.v} value={a.v}>
                {a.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
