'use client';

import { useEffect, useState, useCallback } from 'react';
import { X, Plus, Trash2, Save, Loader2 } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface GTTable {
  id?: string;
  table_index: number;
  headers: string[];
  rows: string[][];
  notes: string;
}

interface Props {
  docId: string;
  filename: string;
  onClose: () => void;
  onSaved: () => void;
}

const emptyTable = (index: number): GTTable => ({
  table_index: index,
  headers: ['Col 1', 'Col 2'],
  rows: [['', '']],
  notes: '',
});

export default function GroundTruthEditor({ docId, filename, onClose, onSaved }: Props) {
  const [tables, setTables] = useState<GTTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    axios.get(`${API}/api/ground-truth/${docId}`)
      .then(r => {
        const data: GTTable[] = r.data.length ? r.data.map((t: any) => ({ ...t, notes: t.notes ?? '' })) : [emptyTable(0)];
        setTables(data);
        setActiveIdx(0);
      })
      .catch(() => setTables([emptyTable(0)]))
      .finally(() => setLoading(false));
  }, [docId]);

  const t = tables[activeIdx];

  const updateTable = useCallback((patch: Partial<GTTable>) => {
    setTables(prev => prev.map((tbl, i) => i === activeIdx ? { ...tbl, ...patch } : tbl));
  }, [activeIdx]);

  const setHeader = (ci: number, val: string) => {
    const headers = [...t.headers];
    headers[ci] = val;
    updateTable({ headers });
  };

  const setCell = (ri: number, ci: number, val: string) => {
    const rows = t.rows.map((r, i) => i === ri ? r.map((c, j) => j === ci ? val : c) : r);
    updateTable({ rows });
  };

  const addColumn = () => updateTable({ headers: [...t.headers, `Col ${t.headers.length + 1}`], rows: t.rows.map(r => [...r, '']) });
  const removeColumn = (ci: number) => updateTable({ headers: t.headers.filter((_, i) => i !== ci), rows: t.rows.map(r => r.filter((_, i) => i !== ci)) });
  const addRow = () => updateTable({ rows: [...t.rows, Array(t.headers.length).fill('')] });
  const removeRow = (ri: number) => updateTable({ rows: t.rows.filter((_, i) => i !== ri) });

  const addTable = () => {
    const next = emptyTable(tables.length);
    setTables(prev => [...prev, next]);
    setActiveIdx(tables.length);
  };

  const save = async () => {
    setSaving(true);
    try {
      for (const tbl of tables) {
        const payload = { table_index: tbl.table_index, headers: tbl.headers, rows: tbl.rows, notes: tbl.notes || null };
        if (tbl.id) {
          await axios.put(`${API}/api/ground-truth/${docId}/${tbl.table_index}`, payload);
        } else {
          await axios.post(`${API}/api/ground-truth/${docId}`, payload);
        }
      }
      toast.success('Ground truth saved');
      onSaved();
      onClose();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Edit Ground Truth</h2>
            <p className="text-sm text-slate-500 truncate max-w-md">{filename}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          </div>
        ) : (
          <>
            {/* Table tabs */}
            <div className="flex items-center gap-2 px-6 pt-4 border-b border-slate-200 dark:border-slate-700">
              {tables.map((tbl, i) => (
                <button
                  key={i}
                  onClick={() => setActiveIdx(i)}
                  className={cn(
                    'px-3 py-1.5 text-sm rounded-t border-b-2 -mb-px transition-colors',
                    i === activeIdx
                      ? 'border-indigo-500 text-indigo-700 dark:text-indigo-300 font-medium'
                      : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  )}
                >
                  Table {tbl.table_index}
                </button>
              ))}
              <button onClick={addTable} className="ml-1 px-2 py-1 text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1">
                <Plus className="w-3.5 h-3.5" /> Add table
              </button>
            </div>

            {/* Editor */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {/* Notes */}
              <div>
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Notes (optional)</label>
                <input
                  type="text"
                  value={t.notes}
                  onChange={e => updateTable({ notes: e.target.value })}
                  placeholder="Edge-case annotations…"
                  className="mt-1 w-full text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Editable table */}
              <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
                <table className="text-xs w-full border-collapse min-w-max">
                  <thead className="bg-slate-50 dark:bg-slate-800">
                    <tr>
                      <th className="w-8 px-2 py-2 border-b border-slate-200 dark:border-slate-700 text-slate-400">#</th>
                      {t.headers.map((h, ci) => (
                        <th key={ci} className="border-b border-slate-200 dark:border-slate-700 p-0">
                          <div className="flex items-center">
                            <input
                              value={h}
                              onChange={e => setHeader(ci, e.target.value)}
                              className="flex-1 px-2 py-2 bg-transparent font-medium text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20 min-w-[80px]"
                            />
                            {t.headers.length > 1 && (
                              <button onClick={() => removeColumn(ci)} className="px-1 text-slate-300 hover:text-red-500 transition-colors">
                                <X className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </th>
                      ))}
                      <th className="border-b border-slate-200 dark:border-slate-700 w-8">
                        <button onClick={addColumn} className="px-2 py-2 text-indigo-500 hover:text-indigo-700 transition-colors">
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {t.rows.map((row, ri) => (
                      <tr key={ri} className="group border-b border-slate-100 dark:border-slate-800 last:border-0">
                        <td className="px-2 py-1 text-center text-slate-300 text-[10px]">{ri + 1}</td>
                        {row.map((cell, ci) => (
                          <td key={ci} className="p-0 border-r border-slate-100 dark:border-slate-800 last:border-0">
                            <input
                              value={cell}
                              onChange={e => setCell(ri, ci, e.target.value)}
                              className="w-full px-2 py-1.5 bg-transparent text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20 min-w-[80px]"
                            />
                          </td>
                        ))}
                        <td className="px-1">
                          <button
                            onClick={() => removeRow(ri)}
                            className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-red-500 transition-all"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button onClick={addRow} className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add row
              </button>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
              <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                Cancel
              </button>
              <button
                onClick={save}
                disabled={saving}
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium flex items-center gap-2 disabled:opacity-60 transition-colors"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
