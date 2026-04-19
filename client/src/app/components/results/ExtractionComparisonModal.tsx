'use client';

import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface ResultRow {
  tool_name: string;
  table_index: number;
  extracted_headers: string[] | null;
  extracted_rows: string[][] | null;
  f1_score: number | null;
  teds_score: number | null;
}

interface GTTable {
  table_index: number;
  headers: string[];
  rows: string[][];
}

interface Props {
  docId: string;
  filename: string;
  toolName: string;
  tableIndex: number;
  onClose: () => void;
}

function TablePreview({ headers, rows, label }: { headers: string[]; rows: string[][]; label: string }) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</h4>
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="text-xs w-full border-collapse min-w-max">
          <thead className="bg-slate-50 dark:bg-slate-800">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-1.5 text-slate-700 dark:text-slate-300">{cell}</td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={headers.length || 1} className="px-3 py-4 text-center text-slate-400">No rows</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ExtractionComparisonModal({ docId, filename, toolName, tableIndex, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [extraction, setExtraction] = useState<ResultRow | null>(null);
  const [groundTruth, setGroundTruth] = useState<GTTable | null>(null);

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/api/results/${docId}`),
      axios.get(`${API}/api/ground-truth/${docId}`),
    ]).then(([resResults, resGT]) => {
      const er = resResults.data.find((r: ResultRow) => r.tool_name === toolName && r.table_index === tableIndex);
      const gt = resGT.data.find((g: GTTable) => g.table_index === tableIndex);
      setExtraction(er ?? null);
      setGroundTruth(gt ?? null);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [docId, toolName, tableIndex]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-[90vw] max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Extraction vs Ground Truth</h2>
            <p className="text-sm text-slate-500">{filename} · Table {tableIndex} · {toolName}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Score badges */}
            {extraction && (
              <div className="flex flex-wrap gap-3">
                {[
                  { label: 'F1', value: extraction.f1_score },
                  { label: 'TEDS', value: extraction.teds_score },
                ].map(({ label, value }) => (
                  <div key={label} className="px-4 py-2 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
                    <div className="text-lg font-bold text-slate-800 dark:text-slate-100">
                      {value != null ? value.toFixed(3) : '—'}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Side-by-side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TablePreview
                headers={extraction?.extracted_headers ?? []}
                rows={extraction?.extracted_rows ?? []}
                label={`Extracted by ${toolName}`}
              />
              <TablePreview
                headers={groundTruth?.headers ?? []}
                rows={groundTruth?.rows ?? []}
                label="Ground Truth"
              />
            </div>

            {!extraction && <p className="text-slate-400 text-sm">No extraction data found for this tool / table.</p>}
            {!groundTruth && <p className="text-amber-500 text-sm">No ground truth found for this table index.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
