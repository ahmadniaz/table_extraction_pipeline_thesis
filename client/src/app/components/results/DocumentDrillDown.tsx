'use client';

import { useState } from 'react';
import { Eye, Loader2 } from 'lucide-react';
import ExtractionComparisonModal from './ExtractionComparisonModal';

interface ResultRow {
  tool_name: string;
  table_index: number;
  processing_time_ms: number | null;
  cost_usd: number | null;
  error: string | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  teds_score: number | null;
  grits_top: number | null;
}

interface Document { id: string; filename: string; }

interface Props {
  documents: Document[];
  resultsByDoc: Record<string, ResultRow[]>;
}

function fmt(v: number | null, d = 3) { return v != null ? v.toFixed(d) : '—'; }

export default function DocumentDrillDown({ documents, resultsByDoc }: Props) {
  const [selectedDocId, setSelectedDocId] = useState<string>(documents[0]?.id ?? '');
  const [comparison, setComparison] = useState<{ tool: string; table: number } | null>(null);

  const selectedDoc = documents.find(d => d.id === selectedDocId);
  const rows = resultsByDoc[selectedDocId] ?? [];

  return (
    <div className="space-y-4">
      {/* Doc selector */}
      <select
        value={selectedDocId}
        onChange={e => setSelectedDocId(e.target.value)}
        className="text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 max-w-md w-full"
      >
        {documents.map(d => (
          <option key={d.id} value={d.id}>{d.filename}</option>
        ))}
      </select>

      {/* Results table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm border-collapse">
          <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Tool</th>
              <th className="px-4 py-3 text-center font-medium">Table</th>
              <th className="px-4 py-3 text-center font-medium">F1</th>
              <th className="px-4 py-3 text-center font-medium">TEDS</th>
              <th className="px-4 py-3 text-center font-medium">GriTS</th>
              <th className="px-4 py-3 text-center font-medium">Time (ms)</th>
              <th className="px-4 py-3 text-center font-medium">Cost ($)</th>
              <th className="px-4 py-3 text-center font-medium">Status</th>
              <th className="px-4 py-3 text-center font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.tool_name}-${r.table_index}-${i}`} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{r.tool_name}</td>
                <td className="px-4 py-3 text-center text-slate-600 dark:text-slate-400">{r.table_index}</td>
                <td className="px-4 py-3 text-center text-slate-700 dark:text-slate-300 tabular-nums">{fmt(r.f1_score)}</td>
                <td className="px-4 py-3 text-center text-slate-700 dark:text-slate-300 tabular-nums">{fmt(r.teds_score)}</td>
                <td className="px-4 py-3 text-center text-slate-700 dark:text-slate-300 tabular-nums">{fmt(r.grits_top)}</td>
                <td className="px-4 py-3 text-center text-slate-600 dark:text-slate-400 tabular-nums">{r.processing_time_ms ?? '—'}</td>
                <td className="px-4 py-3 text-center text-slate-600 dark:text-slate-400 tabular-nums">{r.cost_usd != null ? r.cost_usd.toFixed(5) : '—'}</td>
                <td className="px-4 py-3 text-center">
                  {r.error ? (
                    <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 rounded" title={r.error}>
                      Error
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 rounded">
                      OK
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => setComparison({ tool: r.tool_name, table: r.table_index })}
                    className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-indigo-600 transition-colors"
                    title="View extraction"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-slate-400 text-sm">
                  No results for this document yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Comparison modal */}
      {comparison && selectedDoc && (
        <ExtractionComparisonModal
          docId={selectedDocId}
          filename={selectedDoc.filename}
          toolName={comparison.tool}
          tableIndex={comparison.table}
          onClose={() => setComparison(null)}
        />
      )}
    </div>
  );
}
