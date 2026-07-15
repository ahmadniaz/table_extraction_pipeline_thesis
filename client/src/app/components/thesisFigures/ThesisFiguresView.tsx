'use client';

import { useCallback, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
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
import {
  GRTS_CON_GROUP_COLOR,
  GRTS_TOP_GROUP_COLOR,
  THESIS_STACK_FAIL,
  THESIS_STACK_PARTIAL,
  THESIS_STACK_SUCCESS,
  chartColorForTool,
  chartColorForTier,
} from '@/lib/analytics/chartTheme';
import { ChartCard } from '@/app/components/analytics/ChartCard';
import {
  thesisCostByTierCommercial,
  thesisCostF1Points,
  thesisF1ByToolAll,
  thesisF1ByToolAndThreeTiers,
  thesisF1LineDataThreeTiers,
  thesisFailureStackByTool,
  thesisGriTSGroupedByTool,
  thesisRuntimeF1Points,
} from '@/lib/analytics/thesisFigureData';
import type { DocumentToolAggregate } from '@/lib/analytics/types';

const GRID = '#e5e7eb';
const AXIS = '#374151';
const AXIS_TINY = 11;

type Props = { rows: DocumentToolAggregate[]; docCount: number };

function ScatterWithLabels(props: unknown) {
  const p = props as { cx?: number; cy?: number; payload?: { name: string; toolId: string; x: number; y: number } };
  const { cx = 0, cy = 0, payload } = p;
  if (!payload) return <g />;
  const fill = chartColorForTool(payload.toolId);
  return (
    <g>
      <circle cx={cx} cy={cy} r={5} fill={fill} stroke="#fff" strokeWidth={1} />
      <text x={cx} y={cy - 10} textAnchor="middle" fontSize={10} fill={AXIS} className="font-medium">
        {payload.name}
      </text>
    </g>
  );
}

export function ThesisFiguresView({ rows, docCount }: Props) {
  const data = rows;
  const [includeOssCost, setIncludeOssCost] = useState(false);
  const [rtLog, setRtLog] = useState(false);
  const [lineHidden, setLineHidden] = useState<Set<string>>(() => new Set());
  const [includeCostByTier, setIncludeCostByTier] = useState(false);

  const c1 = useMemo(() => thesisF1ByToolAll(data), [data]);
  const c2 = useMemo(() => thesisF1ByToolAndThreeTiers(data), [data]);
  const c3 = useMemo(() => thesisF1LineDataThreeTiers(data), [data]);
  const c4 = useMemo(() => thesisGriTSGroupedByTool(data), [data]);
  const c5 = useMemo(() => thesisCostF1Points(data, includeOssCost), [data, includeOssCost]);
  const c6raw = useMemo(() => thesisRuntimeF1Points(data), [data]);
  const c6 = useMemo(
    () =>
      c6raw.map(p => ({
        name: p.name,
        toolId: p.toolId,
        y: p.y,
        x: rtLog ? Math.log10(Math.max(p.x, 1)) : p.x,
      })),
    [c6raw, rtLog]
  );
  const c7 = useMemo(() => thesisFailureStackByTool(data), [data]);
  const c8 = useMemo(() => thesisCostByTierCommercial(data), [data]);

  const onLegendLine = useCallback((e: unknown) => {
    const k = (e as { dataKey?: string }).dataKey;
    if (!k || typeof k !== 'string') return;
    setLineHidden(prev => {
      const n = new Set(prev);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });
  }, []);

  const subtitleF1 = docCount
    ? `Mean F1 across all ${docCount} commission statement${docCount === 1 ? '' : 's'}.`
    : 'Mean F1 per document×tool, aggregated by tool.';

  return (
    <div className="space-y-12 [color-scheme:light]">
      <ChartCard
        title="Aggregate F1 Score by Tool"
        subtitle={subtitleF1}
        exportFileName="aggregate-f1-by-tool"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <div className="h-[360px] w-full">
          <ResponsiveContainer>
            <BarChart layout="vertical" data={c1} margin={{ left: 16, right: 56, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 1]}
                tick={{ fontSize: AXIS_TINY, fill: AXIS }}
                tickFormatter={(v: number) => v.toFixed(2)}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={120}
                tick={{ fontSize: AXIS_TINY, fill: AXIS }}
                reversed
              />
              <Tooltip formatter={(v: number) => (typeof v === 'number' ? v.toFixed(4) : v)} />
              <Bar dataKey="value" radius={[0, 2, 2, 0]}>
                {c1.map(e => (
                  <Cell key={e.tool} fill={chartColorForTool(e.tool)} />
                ))}
                <LabelList
                  dataKey="value"
                  position="right"
                  formatter={(v: unknown) => (typeof v === 'number' ? v.toFixed(4) : '')}
                  style={{ fontSize: 10, fill: AXIS }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="F1 Score by Tool Across Complexity Tiers"
        subtitle="Group means (LOW, MEDIUM, HIGH) per tool."
        exportFileName="f1-by-tool-and-tier"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <div className="h-[380px] w-full">
          <ResponsiveContainer>
            <BarChart data={c2} margin={{ left: 8, right: 8, top: 8, bottom: 56 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis
                dataKey="tool"
                tick={{ fontSize: 9, fill: AXIS }}
                angle={-22}
                textAnchor="end"
                height={72}
                interval={0}
              />
              <YAxis type="number" domain={[0, 1]} tick={{ fontSize: AXIS_TINY, fill: AXIS }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="LOW" name="LOW" fill={chartColorForTier('low')} />
              <Bar dataKey="MEDIUM" name="MEDIUM" fill={chartColorForTier('medium')} />
              <Bar dataKey="HIGH" name="HIGH" fill={chartColorForTier('high')} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="Performance Degradation Across Complexity Tiers"
        subtitle="Mean F1 by tool from LOW to HIGH complexity. Click a legend item to show or hide a tool."
        exportFileName="f1-degradation-by-tier"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <div className="h-[380px] w-full">
          <ResponsiveContainer>
            <LineChart data={c3} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="tier" tick={{ fontSize: AXIS_TINY, fill: AXIS }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: AXIS_TINY, fill: AXIS }} />
              <Tooltip />
              <Legend onClick={onLegendLine} wrapperStyle={{ cursor: 'pointer', fontSize: 12 }} />
              {ALL_EVAL_TOOLS.map(t => {
                if (lineHidden.has(t.id)) return null;
                return (
                  <Line
                    key={t.id}
                    type="monotone"
                    dataKey={t.id}
                    name={t.label}
                    stroke={chartColorForTool(t.id)}
                    strokeWidth={2}
                    dot={{ r: 4, strokeWidth: 1, fill: chartColorForTool(t.id) }}
                    connectNulls
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="Structural vs Content Accuracy by Tool"
        subtitle="Aggregate GriTS-Top and GriTS-Con (mean of document×tool scores)."
        exportFileName="grits-top-vs-grits-con-by-tool"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <div className="h-[380px] w-full">
          <ResponsiveContainer>
            <BarChart data={c4} margin={{ left: 8, right: 8, top: 8, bottom: 56 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9, fill: AXIS }}
                angle={-22}
                textAnchor="end"
                height={72}
                interval={0}
              />
              <YAxis type="number" domain={[0, 1]} tick={{ fontSize: AXIS_TINY, fill: AXIS }} />
              <Tooltip formatter={(v: number) => (typeof v === 'number' ? v.toFixed(4) : v)} />
              <Legend />
              <Bar dataKey="gritsTop" name="GriTS-Top" fill={GRTS_TOP_GROUP_COLOR} />
              <Bar dataKey="gritsCon" name="GriTS-Con" fill={GRTS_CON_GROUP_COLOR} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="Cost–Accuracy Trade-off"
        subtitle="Aggregate F1 versus mean cost per page (USD). Commercial tools by default; open-source at $0 when included."
        exportFileName="cost-vs-f1"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <label className="mb-2 flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={includeOssCost}
            onChange={e => setIncludeOssCost(e.target.checked)}
            className="rounded border-slate-300"
          />
          Include open-source tools at zero cost
        </label>
        <div className="h-[340px] w-full">
          <ResponsiveContainer>
            <ScatterChart margin={{ left: 8, right: 8, top: 12, bottom: 28 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis
                type="number"
                dataKey="x"
                name="Cost $/pg"
                tick={{ fontSize: AXIS_TINY, fill: AXIS }}
                label={{ value: 'Cost per page (USD)', position: 'bottom', offset: 0, fontSize: 11, fill: AXIS }}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[0, 1]}
                name="F1"
                tick={{ fontSize: AXIS_TINY, fill: AXIS }}
                label={{ value: 'Aggregate F1', angle: -90, position: 'insideLeft', fontSize: 11, fill: AXIS }}
              />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                formatter={(v: number) => (typeof v === 'number' ? v.toFixed(4) : v)}
              />
              <Scatter name="Tools" data={c5} shape={ScatterWithLabels} isAnimationActive={false} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="Latency–Accuracy Trade-off"
        subtitle="Aggregate F1 versus mean processing time (max table time) per document×tool, averaged by tool."
        exportFileName="runtime-vs-f1"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <label className="mb-2 flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={rtLog} onChange={e => setRtLog(e.target.checked)} className="rounded border-slate-300" />
          Log scale for runtime
        </label>
        <div className="h-[340px] w-full">
          <ResponsiveContainer>
            <ScatterChart margin={{ left: 8, right: 8, top: 12, bottom: 28 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis
                type="number"
                dataKey="x"
                tick={{ fontSize: AXIS_TINY, fill: AXIS }}
                label={{
                  value: rtLog ? 'log10 (mean time, ms)' : 'Mean time (ms)',
                  position: 'bottom',
                  offset: 0,
                  fontSize: 11,
                  fill: AXIS,
                }}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[0, 1]}
                tick={{ fontSize: AXIS_TINY, fill: AXIS }}
                label={{ value: 'Aggregate F1', angle: -90, position: 'insideLeft', fontSize: 11, fill: AXIS }}
              />
              <Tooltip formatter={(v: number) => (typeof v === 'number' ? v.toFixed(4) : v)} />
              <Scatter name="Tools" data={c6} shape={ScatterWithLabels} isAnimationActive={false} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="Failure and Partial-Extraction Cases by Tool"
        subtitle="Count of (document×tool) rows. Successful = scoreable; structural failure; partial or missing/unevaluated F1."
        exportFileName="failure-and-partial-extraction-by-tool"
        thesisStyle
        exportShowCopy={false}
        contentMinHeightClassName="min-h-[300px]"
      >
        <div className="h-[360px] w-full">
          <ResponsiveContainer>
            <BarChart data={c7} margin={{ left: 8, right: 8, top: 8, bottom: 48 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="tool" tick={{ fontSize: 9, fill: AXIS }} angle={-20} textAnchor="end" height={56} />
              <YAxis allowDecimals={false} tick={{ fontSize: AXIS_TINY, fill: AXIS }} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const p = payload[0]?.payload as (typeof c7)[0];
                  if (!p) return null;
                  return (
                    <div className="rounded border border-slate-200 bg-white px-2 py-1.5 text-xs shadow">
                      <div className="font-medium">{p.tool}</div>
                      <div>Successful: {p.successful}</div>
                      <div>Structural failure: {p.structuralFailure}</div>
                      <div>Partial / missing: {p.partialOrMissingF1}</div>
                    </div>
                  );
                }}
              />
              <Legend />
              <Bar dataKey="successful" name="Successful / scoreable" stackId="a" fill={THESIS_STACK_SUCCESS} />
              <Bar dataKey="structuralFailure" name="Complete structural failure" stackId="a" fill={THESIS_STACK_FAIL} />
              <Bar dataKey="partialOrMissingF1" name="Partial or missing F1" stackId="a" fill={THESIS_STACK_PARTIAL} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <div className="border-t border-slate-200 pt-6">
        <label className="mb-3 flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={includeCostByTier}
            onChange={e => setIncludeCostByTier(e.target.checked)}
            className="rounded border-slate-300"
          />
          Show optional figure: per-page cost by tool and complexity tier (commercial tools only)
        </label>
        {includeCostByTier ? (
          <ChartCard
            title="Per-Page Cost by Tool and Complexity Tier"
            subtitle="Commercial tools only. Mean USD per page within each (tool × tier) slice."
            exportFileName="per-page-cost-by-tool-and-complexity-tier"
            thesisStyle
            exportShowCopy={false}
            contentMinHeightClassName="min-h-[300px]"
          >
            {c8.length === 0 ? (
              <p className="text-sm text-slate-500">No commercial cost data for this run.</p>
            ) : (
              <div className="h-[360px] w-full">
                <ResponsiveContainer>
                  <BarChart data={c8} margin={{ left: 8, right: 8, top: 8, bottom: 56 }}>
                    <CartesianGrid stroke={GRID} />
                    <XAxis
                      dataKey="tool"
                      tick={{ fontSize: 9, fill: AXIS }}
                      angle={-20}
                      textAnchor="end"
                      height={56}
                    />
                    <YAxis tick={{ fontSize: AXIS_TINY, fill: AXIS }} tickFormatter={v => v.toFixed(4)} />
                    <Tooltip formatter={(v: number) => (typeof v === 'number' ? v.toFixed(6) : v)} />
                    <Legend />
                    <Bar dataKey="LOW" name="LOW" fill={chartColorForTier('low')} />
                    <Bar dataKey="MEDIUM" name="MEDIUM" fill={chartColorForTier('medium')} />
                    <Bar dataKey="HIGH" name="HIGH" fill={chartColorForTier('high')} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartCard>
        ) : null}
      </div>
    </div>
  );
}
