'use client';

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { X, Plus, Trash2, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';
import * as pdfjsLib from 'pdfjs-dist';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.js`;
}

interface GTTable {
  id?: string;
  table_index: number;
  headers: string[];
  rows: string[][];
  notes: string;
  source?: string;
  confirmed?: boolean;
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
  source: 'manual',
  confirmed: false,
});

type OriginalSnap = { headers: string[]; rows: string[][] };

function deepCloneTable(h: string[], r: string[][]): OriginalSnap {
  return { headers: [...h], rows: r.map(row => [...row]) };
}

function PdfPanel({ docId, filename }: { docId: string; filename: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const url = `${API}/api/documents/${docId}/pdf`;
    (async () => {
      try {
        const task = pdfjsLib.getDocument({ url, withCredentials: false });
        const doc = await task.promise;
        if (!cancelled) {
          setPdf(doc);
          setPageNum(1);
        }
      } catch (e: unknown) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Failed to load PDF');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId]);

  useEffect(() => {
    if (!pdf || !canvasRef.current) return;
    let cancelled = false;
    (async () => {
      const page = await pdf.getPage(pageNum);
      if (cancelled) return;
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const vp = page.getViewport({ scale: 1.2 });
      canvas.width = vp.width;
      canvas.height = vp.height;
      await page.render({ canvasContext: ctx, viewport: vp }).promise;
    })();
    return () => {
      cancelled = true;
    };
  }, [pdf, pageNum]);

  const total = pdf?.numPages ?? 0;

  return (
    <div className="flex flex-col h-full min-h-0 border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-950 overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-700 text-xs font-medium text-slate-600 dark:text-slate-300 truncate">
        {filename}
      </div>
      <div className="flex-1 overflow-auto flex items-start justify-center p-3">
        {loading && (
          <div className="flex flex-col items-center gap-2 py-12 text-slate-500">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span className="text-xs">Loading PDF…</span>
          </div>
        )}
        {err && !loading && (
          <p className="text-xs text-red-600 dark:text-red-400 p-4 text-center">{err}</p>
        )}
        {!loading && !err && (
          <canvas ref={canvasRef} className="shadow-md max-w-full h-auto" />
        )}
      </div>
      {total > 1 && (
        <div className="flex items-center justify-center gap-2 py-2 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <button
            type="button"
            disabled={pageNum <= 1}
            onClick={() => setPageNum(p => Math.max(1, p - 1))}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-slate-600 dark:text-slate-400 tabular-nums">
            {pageNum} / {total}
          </span>
          <button
            type="button"
            disabled={pageNum >= total}
            onClick={() => setPageNum(p => Math.min(total, p + 1))}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export default function GroundTruthEditor({ docId, filename, onClose, onSaved }: Props) {
  const router = useRouter();
  const [tables, setTables] = useState<GTTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const originalsRef = useRef<Map<number, OriginalSnap>>(new Map());

  useEffect(() => {
    axios
      .get(`${API}/api/ground-truth/${docId}`)
      .then(r => {
        const data: GTTable[] = r.data.length
          ? r.data.map((t: GTTable & { notes?: string | null }) => ({
              ...t,
              notes: t.notes ?? '',
              source: t.source ?? 'manual',
              confirmed: t.confirmed ?? false,
            }))
          : [emptyTable(0)];
        setTables(data);
        setActiveIdx(0);
        const m = new Map<number, OriginalSnap>();
        for (const tbl of data) {
          m.set(tbl.table_index, deepCloneTable(tbl.headers, tbl.rows));
        }
        originalsRef.current = m;
      })
      .catch(() => {
        const t = emptyTable(0);
        setTables([t]);
        originalsRef.current = new Map([[0, deepCloneTable(t.headers, t.rows)]]);
      })
      .finally(() => setLoading(false));
  }, [docId]);

  const t = tables[activeIdx];
  const showSeedBanner =
    t && typeof t.source === 'string' && t.source.endsWith('_seed') && !t.confirmed;

  const correctionCount = useMemo(() => {
    let n = 0;
    const origMap = originalsRef.current;
    for (const tbl of tables) {
      const o = origMap.get(tbl.table_index);
      if (!o) continue;
      tbl.headers.forEach((h, ci) => {
        if (h !== (o.headers[ci] ?? '')) n += 1;
      });
      tbl.rows.forEach((row, ri) => {
        row.forEach((cell, ci) => {
          if (cell !== (o.rows[ri]?.[ci] ?? '')) n += 1;
        });
      });
    }
    return n;
  }, [tables]);

  const isCellEdited = useCallback(
    (tbl: GTTable, ri: number, ci: number, val: string) => {
      const o = originalsRef.current.get(tbl.table_index);
      if (!o) return false;
      if (ri === -1) return val !== (o.headers[ci] ?? '');
      return val !== (o.rows[ri]?.[ci] ?? '');
    },
    []
  );

  const updateTable = useCallback((patch: Partial<GTTable>) => {
    setTables(prev => prev.map((tbl, i) => (i === activeIdx ? { ...tbl, ...patch } : tbl)));
  }, [activeIdx]);

  const setHeader = (ci: number, val: string) => {
    if (!t) return;
    const headers = [...t.headers];
    headers[ci] = val;
    updateTable({ headers });
  };

  const setCell = (ri: number, ci: number, val: string) => {
    if (!t) return;
    const rows = t.rows.map((r, i) => (i === ri ? r.map((c, j) => (j === ci ? val : c)) : r));
    updateTable({ rows });
  };

  const addColumn = () =>
    t && updateTable({ headers: [...t.headers, `Col ${t.headers.length + 1}`], rows: t.rows.map(r => [...r, '']) });
  const removeColumn = (ci: number) =>
    t &&
    updateTable({
      headers: t.headers.filter((_, i) => i !== ci),
      rows: t.rows.map(r => r.filter((_, i) => i !== ci)),
    });
  const addRow = () => t && updateTable({ rows: [...t.rows, Array(t.headers.length).fill('')] });
  const removeRow = (ri: number) => t && updateTable({ rows: t.rows.filter((_, i) => i !== ri) });

  const addTable = () => {
    setTables(prev => {
      const nextIdx = prev.length ? Math.max(...prev.map(x => x.table_index), -1) + 1 : 0;
      const next = emptyTable(nextIdx);
      originalsRef.current.set(nextIdx, deepCloneTable(next.headers, next.rows));
      setActiveIdx(prev.length);
      return [...prev, next];
    });
  };

  const buildCorrectionLogForTable = (tbl: GTTable) => {
    const o = originalsRef.current.get(tbl.table_index);
    if (!o) return [];
    const log: { row: number; col: number; original: string; corrected: string }[] = [];
    tbl.headers.forEach((h, ci) => {
      const oh = o.headers[ci] ?? '';
      if (h !== oh) log.push({ row: -1, col: ci, original: oh, corrected: h });
    });
    tbl.rows.forEach((row, ri) => {
      row.forEach((cell, ci) => {
        const oc = o.rows[ri]?.[ci] ?? '';
        if (cell !== oc) log.push({ row: ri, col: ci, original: oc, corrected: cell });
      });
    });
    return log;
  };

  const confirm = async () => {
    setSaving(true);
    try {
      const payload = {
        tables: tables.map(tbl => ({
          table_index: tbl.table_index,
          headers: tbl.headers,
          rows: tbl.rows,
          notes: tbl.notes || null,
          correction_log: buildCorrectionLogForTable(tbl),
        })),
      };
      await axios.post(`${API}/api/ground-truth/${docId}/confirm`, payload);
      toast.success('Ground truth confirmed');
      onSaved();
      onClose();
      router.push(`/evaluation/${docId}`);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } };
      toast.error(ax?.response?.data?.detail ?? 'Confirm failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/50">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-[min(98vw,1400px)] h-[min(95vh,900px)] flex flex-col">
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Ground truth</h2>
            <p className="text-sm text-slate-500 truncate max-w-md">{filename}</p>
            {!loading && (
              <p className="text-xs text-slate-500 mt-1">
                <span className="font-medium text-indigo-600 dark:text-indigo-400">{correctionCount}</span> cells
                corrected
              </p>
            )}
          </div>
          <button type="button" onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          </div>
        ) : (
          <div className="flex-1 flex flex-col lg:flex-row min-h-0">
            <div className="w-full lg:w-[40%] min-h-[200px] lg:min-h-0 p-3 lg:border-r border-slate-200 dark:border-slate-700 shrink-0">
              <PdfPanel docId={docId} filename={filename} />
            </div>

            <div className="flex-1 flex flex-col min-h-0 min-w-0">
              {showSeedBanner && (
                <div className="mx-3 mt-3 px-3 py-2 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-200 text-sm border border-amber-200 dark:border-amber-800">
                  Pre-extracted by an automated tool (seed). Verify every cell before confirming.
                </div>
              )}

              <div className="flex items-center gap-2 px-3 pt-3 border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
                {tables.map((tbl, i) => (
                  <button
                    key={tbl.table_index}
                    type="button"
                    onClick={() => setActiveIdx(i)}
                    className={cn(
                      'px-3 py-1.5 text-sm rounded-t border-b-2 -mb-px whitespace-nowrap transition-colors',
                      i === activeIdx
                        ? 'border-indigo-500 text-indigo-700 dark:text-indigo-300 font-medium'
                        : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                    )}
                  >
                    Table {tbl.table_index}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={addTable}
                  className="ml-1 px-2 py-1 text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" /> Add table
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {t && (
                  <>
                    <div>
                      <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                        Notes (optional)
                      </label>
                      <input
                        type="text"
                        value={t.notes}
                        onChange={e => updateTable({ notes: e.target.value })}
                        placeholder="Edge-case annotations…"
                        className="mt-1 w-full text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
                      <table className="text-xs w-full border-collapse min-w-max">
                        <thead className="bg-slate-50 dark:bg-slate-800">
                          <tr>
                            <th className="w-8 px-2 py-2 border-b border-slate-200 dark:border-slate-700 text-slate-400">#</th>
                            {t.headers.map((h, ci) => (
                              <th key={ci} className="border-b border-slate-200 dark:border-slate-700 p-0 relative">
                                <div className="flex items-center">
                                  <input
                                    value={h}
                                    onChange={e => setHeader(ci, e.target.value)}
                                    className={cn(
                                      'flex-1 px-2 py-2 bg-transparent font-medium text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20 min-w-[80px]',
                                      isCellEdited(t, -1, ci, h) && 'ring-1 ring-amber-400 dark:ring-amber-600 rounded'
                                    )}
                                  />
                                  {isCellEdited(t, -1, ci, h) && (
                                    <span className="absolute top-1 right-6 w-1.5 h-1.5 rounded-full bg-amber-500" title="Edited" />
                                  )}
                                  {t.headers.length > 1 && (
                                    <button
                                      type="button"
                                      onClick={() => removeColumn(ci)}
                                      className="px-1 text-slate-300 hover:text-red-500 transition-colors"
                                    >
                                      <X className="w-3 h-3" />
                                    </button>
                                  )}
                                </div>
                              </th>
                            ))}
                            <th className="border-b border-slate-200 dark:border-slate-700 w-8">
                              <button type="button" onClick={addColumn} className="px-2 py-2 text-indigo-500 hover:text-indigo-700">
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
                                <td key={ci} className="p-0 border-r border-slate-100 dark:border-slate-800 last:border-0 relative">
                                  <input
                                    value={cell}
                                    onChange={e => setCell(ri, ci, e.target.value)}
                                    className={cn(
                                      'w-full px-2 py-1.5 bg-transparent text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20 min-w-[80px]',
                                      isCellEdited(t, ri, ci, cell) && 'ring-1 ring-amber-400 dark:ring-amber-600'
                                    )}
                                  />
                                  {isCellEdited(t, ri, ci, cell) && (
                                    <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-500" title="Edited" />
                                  )}
                                </td>
                              ))}
                              <td className="px-1">
                                <button
                                  type="button"
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
                    <button
                      type="button"
                      onClick={addRow}
                      className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" /> Add row
                    </button>
                  </>
                )}
              </div>

              <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex justify-between gap-3 shrink-0 bg-white dark:bg-slate-900">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirm}
                  disabled={saving || !tables.length}
                  className="px-4 py-2 text-sm rounded-lg bg-violet-600 hover:bg-violet-700 text-white font-medium flex items-center gap-2 disabled:opacity-60 transition-colors"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Confirm Ground Truth
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
