'use client';

import { useState } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ToolSummary {
  tool_name: string;
  avg_precision: number | null;
  avg_recall: number | null;
  avg_f1: number | null;
  avg_teds: number | null;
  avg_grits_top: number | null;
  avg_grits_con: number | null;
  cost_per_page: number | null;
  total_cost_usd: number | null;
  avg_time_ms: number | null;
}

type SortKey = keyof ToolSummary;

function fmt(v: number | null, digits = 3) {
  if (v == null) return '—';
  return v.toFixed(digits);
}

const COLUMNS: { key: SortKey; label: string; digits?: number }[] = [
  { key: 'tool_name',     label: 'Tool' },
  { key: 'avg_precision', label: 'Precision' },
  { key: 'avg_recall',    label: 'Recall' },
  { key: 'avg_f1',        label: 'F1' },
  { key: 'avg_teds',      label: 'TEDS' },
  { key: 'avg_grits_top', label: 'GriTS-Top' },
  { key: 'avg_grits_con', label: 'GriTS-Con' },
  { key: 'cost_per_page',   label: 'Cost/Page',   digits: 5 },
  { key: 'total_cost_usd',  label: 'Total cost',  digits: 4 },
  { key: 'avg_time_ms',     label: 'Avg ms',      digits: 0 },
];

interface Props { data: ToolSummary[]; }

export default function MetricsSummaryTable({ data }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('avg_f1');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table className="w-full text-sm border-collapse">
        <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase tracking-wide">
          <tr>
            {COLUMNS.map(col => (
              <th key={col.key} className="px-4 py-3 text-left">
                <button
                  onClick={() => toggleSort(col.key)}
                  className="flex items-center gap-1 font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors whitespace-nowrap"
                >
                  {col.label}
                  {sortKey === col.key
                    ? sortDir === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />
                    : <ArrowUpDown className="w-3 h-3 opacity-30" />
                  }
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.tool_name} className={cn('border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors', i === 0 && 'border-t-0')}>
              <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200 whitespace-nowrap">{row.tool_name}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.avg_precision)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.avg_recall)}</td>
              <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200 tabular-nums">{fmt(row.avg_f1)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.avg_teds)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.avg_grits_top)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.avg_grits_con)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.cost_per_page, 5)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.total_cost_usd, 4)}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400 tabular-nums">{fmt(row.avg_time_ms, 0)}</td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-400 text-sm">No results yet. Run an evaluation first.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
