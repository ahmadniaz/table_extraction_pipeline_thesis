'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface GroundTruthTable {
  id: string;
  table_index: number;
  headers: string[];
  rows: string[][];
  notes?: string;
  annotated_at: string;
}

interface Props {
  docId: string;
  filename: string;
  onClose: () => void;
}

export default function GroundTruthModal({ docId, filename, onClose }: Props) {
  const [tables, setTables] = useState<GroundTruthTable[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/api/ground-truth/${docId}`)
      .then(r => setTables(r.data))
      .catch(() => setTables([]))
      .finally(() => setLoading(false));
  }, [docId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Ground Truth</h2>
            <p className="text-sm text-slate-500 truncate max-w-md">{filename}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && <p className="text-slate-500 text-sm">Loading…</p>}
          {!loading && tables.length === 0 && (
            <p className="text-slate-400 text-sm">No ground truth tables yet. Use &ldquo;Edit Ground Truth&rdquo; to add them.</p>
          )}
          {tables.map(t => (
            <div key={t.id} className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Table {t.table_index}</span>
                {t.notes && <span className="text-xs text-slate-400 italic">{t.notes}</span>}
              </div>
              <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
                <table className="text-xs w-full border-collapse">
                  <thead className="bg-slate-50 dark:bg-slate-800">
                    <tr>
                      {t.headers.map((h, i) => (
                        <th key={i} className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {t.rows.map((row, ri) => (
                      <tr key={ri} className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                        {row.map((cell, ci) => (
                          <td key={ci} className="px-3 py-1.5 text-slate-700 dark:text-slate-300">{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
