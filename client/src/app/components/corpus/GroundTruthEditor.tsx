'use client';

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { X, Plus, Trash2, Loader2, ChevronLeft, ChevronRight, Undo2 } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';
import { sharedGetGroundTruth } from '@/lib/sharedGroundTruthGet';
import * as pdfjsLib from 'pdfjs-dist';
import './groundTruthPdfTextLayer.css';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.js`;
}

interface GTTable {
  id?: string;
  /** Stable client-only id for tables not yet persisted (used for edit baselines). */
  clientKey?: string;
  table_index: number;
  headers: string[];
  rows: string[][];
  notes: string;
  source?: string;
  confirmed?: boolean;
  /** Server-persisted audit trail (e.g. manual merge); preserved on confirm. */
  correction_log?: unknown[];
}

/** LLM placeholder headers: Column 1, Column 2, … */
function hasAutoNamedHeaders(headers: string[]): boolean {
  return (
    headers.length > 0 &&
    headers.every((h, i) => h.trim().toLowerCase() === `column ${i + 1}`)
  );
}

interface Props {
  docId: string;
  filename: string;
  onClose: () => void;
  onSaved: () => void;
}

interface DocLabels {
  complexity_tier: string;
  is_digital: boolean | null;
}

function newClientKey(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `ck-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const emptyTable = (index: number): GTTable => ({
  clientKey: newClientKey(),
  table_index: index,
  headers: ['Col 1', 'Col 2'],
  rows: [['', '']],
  notes: '',
  source: 'manual',
  confirmed: false,
});

/** Baseline snapshots must be keyed by stable identity — not table_index (reorders on delete). */
function baselineKey(tbl: GTTable): string {
  if (tbl.id) return `id:${tbl.id}`;
  if (tbl.clientKey) return `ck:${tbl.clientKey}`;
  return `idx:${tbl.table_index}`;
}

type OriginalSnap = { headers: string[]; rows: string[][] };

function deepCloneTable(h: string[], r: string[][]): OriginalSnap {
  return { headers: [...h], rows: r.map(row => [...row]) };
}

/** Pad or trim so row length matches `len` (orphan cells beyond headers are dropped for display/storage). */
function padRowToLength(row: string[] | undefined, len: number): string[] {
  const r = [...(row || [])];
  while (r.length < len) r.push('');
  return r.slice(0, len);
}

/**
 * When extraction has more cells than headers (or fewer), align counts: add placeholder headers
 * for extra cells, pad short rows. Prevents ghost columns in the grid.
 */
function reconcileColumnCounts(tbl: GTTable): GTTable {
  const maxR = tbl.rows.length ? Math.max(0, ...tbl.rows.map(r => r.length)) : 0;
  const hLen = tbl.headers.length;
  const target = Math.max(hLen, maxR, 1);
  const headers = [...tbl.headers];
  while (headers.length < target) {
    headers.push(`Col ${headers.length + 1}`);
  }
  const rows = tbl.rows.map(r => padRowToLength(r, headers.length));
  return { ...tbl, headers, rows };
}

function normaliseTables(tables: GTTable[]): GTTable[] {
  return tables.map((tbl, idx) => ({
    ...tbl,
    table_index: idx,
  }));
}

/** First table (by order) whose server log still has an undoable merge snapshot. */
function survivorIdWithMergeUndo(mapped: GTTable[]): string | null {
  for (const t of mapped) {
    if (!t.id || !Array.isArray(t.correction_log)) continue;
    if (
      t.correction_log.some(
        e =>
          typeof e === 'object' &&
          e !== null &&
          'type' in e &&
          (e as { type?: string }).type === 'merge_undo'
      )
    ) {
      return t.id;
    }
  }
  return null;
}

function PdfPanel({ docId, filename }: { docId: string; filename: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const textLayerRef = useRef<HTMLDivElement>(null);
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [scale, setScale] = useState(1.2);
  const [renderSize, setRenderSize] = useState({ width: 0, height: 0 });
  const MIN_SCALE = 0.5;
  const MAX_SCALE = 3.0;
  const SCALE_STEP = 0.25;
  const DEFAULT_SCALE = 1.2;

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
    let textTask: { cancel?: () => void } | null = null;
    (async () => {
      const page = await pdf.getPage(pageNum);
      if (cancelled) return;
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const vp = page.getViewport({ scale });
      canvas.width = vp.width;
      canvas.height = vp.height;
      if (!cancelled) setRenderSize({ width: vp.width, height: vp.height });
      await page.render({ canvasContext: ctx, viewport: vp }).promise;
      if (cancelled) return;
      const layerEl = textLayerRef.current;
      if (layerEl) {
        layerEl.innerHTML = '';
        try {
          const textContent = await page.getTextContent();
          if (cancelled) return;
          const renderTextLayer = pdfjsLib.renderTextLayer;
          if (typeof renderTextLayer === 'function') {
            const task = renderTextLayer({
              textContentSource: textContent,
              container: layerEl,
              viewport: vp,
              textDivs: [],
            });
            textTask = task;
            await task.promise;
          }
        } catch {
          // Scanned or malformed text streams — canvas still usable
        }
      }
    })();
    return () => {
      cancelled = true;
      textTask?.cancel?.();
    };
  }, [pdf, pageNum, scale]);

  const total = pdf?.numPages ?? 0;

  return (
    <div className="flex flex-col h-full min-h-0 border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-950 overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-700 text-xs font-medium text-slate-600 dark:text-slate-300 truncate">
        {filename}
      </div>
      <div className="px-3 py-1.5 border-b border-slate-200 dark:border-slate-700 flex flex-wrap items-center gap-2 bg-white/80 dark:bg-slate-900/80">
        <button
          type="button"
          disabled={!pdf || scale <= MIN_SCALE}
          onClick={() => setScale(s => Math.max(MIN_SCALE, +(s - SCALE_STEP).toFixed(2)))}
          className="px-2 py-0.5 text-sm rounded border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
          aria-label="Zoom out"
        >
          −
        </button>
        <span className="text-xs text-slate-600 dark:text-slate-400 tabular-nums min-w-[3rem] text-center">
          {Math.round(scale * 100)}%
        </span>
        <button
          type="button"
          disabled={!pdf || scale >= MAX_SCALE}
          onClick={() => setScale(s => Math.min(MAX_SCALE, +(s + SCALE_STEP).toFixed(2)))}
          className="px-2 py-0.5 text-sm rounded border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          type="button"
          disabled={!pdf || Math.abs(scale - DEFAULT_SCALE) < 0.001}
          onClick={() => setScale(DEFAULT_SCALE)}
          className="px-2 py-0.5 text-xs rounded border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
        >
          Reset
        </button>
      </div>
      <div className="flex-1 overflow-auto flex flex-col min-h-0 w-full p-3">
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
          <div className="overflow-auto flex-1 w-full min-h-0">
            <div
              className="relative shadow-md"
              style={{
                width: renderSize.width || undefined,
                height: renderSize.height || undefined,
              }}
            >
              <canvas ref={canvasRef} className="block" style={{ display: 'block' }} />
              <div ref={textLayerRef} className="textLayer ground-truth-pdf-text-layer" />
            </div>
          </div>
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
  const [docLabels, setDocLabels] = useState<DocLabels | null>(null);
  const [docLabelsLoading, setDocLabelsLoading] = useState(true);
  const [activeIdx, setActiveIdx] = useState(0);
  const [mergingTableId, setMergingTableId] = useState<string | null>(null);
  const [mergeTargetId, setMergeTargetId] = useState<string | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [flashSurvivorId, setFlashSurvivorId] = useState<string | null>(null);
  /** Survivor table id after last merge — undo pops merge stack on the server for this row. */
  const [mergeUndoSurvivorId, setMergeUndoSurvivorId] = useState<string | null>(null);
  /** When set, overrides the diff-based correction count for display (this session only). */
  const [manualCellsCorrected, setManualCellsCorrected] = useState<number | null>(null);
  const originalsRef = useRef<Map<string, OriginalSnap>>(new Map());
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (!flashSurvivorId) return;
    const timer = window.setTimeout(() => setFlashSurvivorId(null), 500);
    return () => window.clearTimeout(timer);
  }, [flashSurvivorId]);

  /**
   * @param baselineMode `server` — replace all edit baselines (initial load, API reload).
   *   `preserve` — keep baselines for tables that still exist (delete/add tab locally).
   */
  const resetTables = useCallback(
    (next: GTTable[], nextActiveIdx: number, baselineMode: 'server' | 'preserve' = 'server') => {
      const norm = normaliseTables(next.map(reconcileColumnCounts));
      setTables(norm);
      if (baselineMode === 'server') {
        const m = new Map<string, OriginalSnap>();
        for (const tbl of norm) {
          m.set(baselineKey(tbl), deepCloneTable(tbl.headers, tbl.rows));
        }
        originalsRef.current = m;
      } else {
        const m = new Map<string, OriginalSnap>(originalsRef.current);
        const seen = new Set<string>();
        for (const tbl of norm) {
          const k = baselineKey(tbl);
          seen.add(k);
          if (!m.has(k)) {
            m.set(k, deepCloneTable(tbl.headers, tbl.rows));
          }
        }
        for (const key of [...m.keys()]) {
          if (!seen.has(key)) m.delete(key);
        }
        originalsRef.current = m;
      }
      setActiveIdx(Math.max(0, Math.min(nextActiveIdx, norm.length - 1)));
    },
    []
  );

  useEffect(() => {
    fetchedRef.current = false;
    setMergingTableId(null);
    setMergeTargetId(null);
    setMergeUndoSurvivorId(null);
    setManualCellsCorrected(null);
  }, [docId]);

  useEffect(() => {
    let cancelled = false;
    setDocLabelsLoading(true);
    (async () => {
      try {
        const { data } = await axios.get<DocLabels>(`${API}/api/documents/${docId}`);
        if (!cancelled) {
          setDocLabels({
            complexity_tier: data.complexity_tier || 'unconfirmed',
            is_digital: data.is_digital ?? null,
          });
        }
      } catch {
        if (!cancelled) {
          setDocLabels({ complexity_tier: 'unconfirmed', is_digital: null });
        }
      } finally {
        if (!cancelled) setDocLabelsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId]);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    let cancelled = false;
    setLoading(true);
    sharedGetGroundTruth(docId)
      .then(r => {
        const raw = r.data as GTTable[];
        const data: GTTable[] = raw.length
          ? raw.map((t: GTTable & { notes?: string | null; correction_log?: unknown[] }) => ({
              ...t,
              notes: t.notes ?? '',
              source: t.source ?? 'manual',
              confirmed: t.confirmed ?? false,
              correction_log: Array.isArray(t.correction_log) ? t.correction_log : [],
            }))
          : [emptyTable(0)];
        if (!cancelled) {
          resetTables(data, 0);
          setMergeUndoSurvivorId(survivorIdWithMergeUndo(data));
        }
      })
      .catch(() => {
        if (!cancelled) {
          resetTables([emptyTable(0)], 0);
          setMergeUndoSurvivorId(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [docId, resetTables]);

  const reloadGroundTruthFromServer = useCallback(
    async (preferredActiveIndex: number, preferredTableId?: string | null) => {
      const { data } = await axios.get<
        (GTTable & { notes?: string | null; id?: string })[]
      >(`${API}/api/ground-truth/${docId}`);
      const mapped: GTTable[] = data.map(t => ({
        ...t,
        notes: t.notes ?? '',
        source: t.source ?? 'manual',
        confirmed: t.confirmed ?? false,
        correction_log: Array.isArray(t.correction_log) ? t.correction_log : [],
      }));
      let idx = Math.max(0, Math.min(preferredActiveIndex, mapped.length - 1));
      if (preferredTableId) {
        const found = mapped.findIndex(t => t.id === preferredTableId);
        if (found >= 0) idx = found;
      }
      resetTables(mapped, idx);
      setMergeUndoSurvivorId(survivorIdWithMergeUndo(mapped));
    },
    [docId, resetTables]
  );

  const handleConfirmMerge = async () => {
    if (!mergingTableId || !mergeTargetId) return;
    setIsMerging(true);
    try {
      const { data: merged } = await axios.post<{
        id: string;
        table_index: number;
      }>(`${API}/api/documents/${docId}/ground-truth/merge`, {
        primary_table_id: mergingTableId,
        secondary_table_id: mergeTargetId,
      });
      setMergingTableId(null);
      setMergeTargetId(null);
      await reloadGroundTruthFromServer(0, merged.id);
      setFlashSurvivorId(merged.id);
      toast.success('Tables merged');
    } catch (err: unknown) {
      const ax = err as { response?: { data?: unknown }; message?: string };
      const detail =
        typeof ax.response?.data === 'object' && ax.response?.data && 'detail' in ax.response.data
          ? String((ax.response.data as { detail: string }).detail)
          : ax.message ?? 'Merge failed';
      console.error('Merge failed:', err);
      toast.error(detail);
    } finally {
      setIsMerging(false);
    }
  };

  const handleUndoMerge = async () => {
    if (!mergeUndoSurvivorId) return;
    setIsMerging(true);
    try {
      const { data } = await axios.post<{
        survivor_table_id: string;
        can_undo_more: boolean;
      }>(`${API}/api/documents/${docId}/ground-truth/merge/undo`, {
        survivor_table_id: mergeUndoSurvivorId,
      });
      await reloadGroundTruthFromServer(0, data.survivor_table_id);
      toast.success('Merge undone');
    } catch (err: unknown) {
      const ax = err as { response?: { data?: unknown }; message?: string };
      const detail =
        typeof ax.response?.data === 'object' && ax.response?.data && 'detail' in ax.response.data
          ? String((ax.response.data as { detail: string }).detail)
          : ax.message ?? 'Undo failed';
      toast.error(detail);
    } finally {
      setIsMerging(false);
    }
  };

  const deleteTableAt = useCallback(
    (arrayIndex: number) => {
      if (tables.length === 1) {
        resetTables([emptyTable(0)], 0, 'server');
        return;
      }
      const next = tables.filter((_, i) => i !== arrayIndex);
      let na = activeIdx;
      if (arrayIndex < activeIdx) na = activeIdx - 1;
      else if (arrayIndex === activeIdx) na = Math.min(activeIdx, next.length - 1);
      resetTables(next, na, 'preserve');
    },
    [tables, activeIdx, resetTables]
  );

  const addTable = useCallback(() => {
    resetTables([...tables, emptyTable(0)], tables.length, 'preserve');
  }, [tables, resetTables]);

  const t = tables[activeIdx];
  const showSeedBanner =
    t && typeof t.source === 'string' && t.source.endsWith('_seed') && !t.confirmed;

  const correctionCount = useMemo(() => {
    let n = 0;
    const origMap = originalsRef.current;
    for (const tbl of tables) {
      const o = origMap.get(baselineKey(tbl));
      if (!o) continue;
      const oh = padRowToLength(o.headers, tbl.headers.length);
      tbl.headers.forEach((h, ci) => {
        if (h !== (oh[ci] ?? '')) n += 1;
      });
      tbl.rows.forEach((row, ri) => {
        const r = padRowToLength(row, tbl.headers.length);
        const ob = padRowToLength(o.rows[ri], tbl.headers.length);
        tbl.headers.forEach((_, ci) => {
          if (r[ci] !== (ob[ci] ?? '')) n += 1;
        });
      });
    }
    return n;
  }, [tables]);

  const displayedCellsCorrected =
    manualCellsCorrected !== null ? manualCellsCorrected : correctionCount;

  const isCellEdited = useCallback(
    (tbl: GTTable, ri: number, ci: number, val: string) => {
      const o = originalsRef.current.get(baselineKey(tbl));
      if (!o) return false;
      if (ri === -1) {
        const oh = padRowToLength(o.headers, tbl.headers.length);
        return val !== (oh[ci] ?? '');
      }
      const orow = padRowToLength(o.rows[ri], tbl.headers.length);
      return val !== (orow[ci] ?? '');
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
    const w = t.headers.length;
    const rows = t.rows.map((r, i) => {
      const base = padRowToLength(r, w);
      if (i !== ri) return base;
      return base.map((c, j) => (j === ci ? val : c));
    });
    updateTable({ rows });
  };

  /** Insert an empty column after column `afterIndex` (use `afterIndex === -1` to insert at the start). */
  const insertColumnAfter = (afterIndex: number) => {
    if (!t || t.headers.length === 0) return;
    const w = t.headers.length;
    const insertAt = Math.min(Math.max(afterIndex + 1, 0), w);
    const nextName = `Col ${w + 1}`;
    const headers = [...t.headers.slice(0, insertAt), nextName, ...t.headers.slice(insertAt)];
    const rows = t.rows.map(r => {
      const p = padRowToLength(r, w);
      return [...p.slice(0, insertAt), '', ...p.slice(insertAt)];
    });
    updateTable({ headers, rows });
  };

  /** Append one column at the right. */
  const addColumn = () => {
    if (!t) return;
    insertColumnAfter(t.headers.length - 1);
  };

  const removeColumn = (ci: number) =>
    t &&
    updateTable({
      headers: t.headers.filter((_, i) => i !== ci),
      rows: t.rows.map(r => padRowToLength(r, t.headers.length).filter((_, i) => i !== ci)),
    });
  const addRow = () =>
    t && updateTable({ rows: [...t.rows.map(r => padRowToLength(r, t.headers.length)), Array(t.headers.length).fill('')] });
  const removeRow = (ri: number) => t && updateTable({ rows: t.rows.filter((_, i) => i !== ri) });

  const buildCorrectionLogForTable = (tbl: GTTable) => {
    const o = originalsRef.current.get(baselineKey(tbl));
    if (!o) return [];
    const log: { row: number; col: number; original: string; corrected: string }[] = [];
    const oh0 = padRowToLength(o.headers, tbl.headers.length);
    tbl.headers.forEach((h, ci) => {
      const oh = oh0[ci] ?? '';
      if (h !== oh) log.push({ row: -1, col: ci, original: oh, corrected: h });
    });
    tbl.rows.forEach((row, ri) => {
      const r = padRowToLength(row, tbl.headers.length);
      const ob = padRowToLength(o.rows[ri], tbl.headers.length);
      tbl.headers.forEach((_, ci) => {
        const cell = r[ci] ?? '';
        const oc = ob[ci] ?? '';
        if (cell !== oc) log.push({ row: ri, col: ci, original: oc, corrected: cell });
      });
    });
    return log;
  };

  const confirm = async () => {
    if (docLabelsLoading || !docLabels) {
      toast.error('Document settings are still loading. Try again in a moment.');
      return;
    }
    if (docLabels.complexity_tier === 'unconfirmed') {
      toast.error('Choose a complexity tier (Low, Medium, or High) before confirming ground truth.');
      return;
    }
    setSaving(true);
    try {
      await axios.patch(`${API}/api/documents/${docId}/tier`, {
        complexity_tier: docLabels.complexity_tier,
        is_digital: docLabels.is_digital,
      });
      const payload = {
        tables: tables.map((tbl, idx) => ({
          table_index: idx,
          headers: tbl.headers,
          rows: tbl.rows,
          notes: tbl.notes || null,
          correction_log: [
            ...(Array.isArray(tbl.correction_log) ? tbl.correction_log : []),
            ...buildCorrectionLogForTable(tbl),
          ],
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
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                <label htmlFor="gt-cells-corrected" className="inline-flex items-center gap-2">
                  <span>Cells corrected</span>
                  <input
                    id="gt-cells-corrected"
                    type="number"
                    min={0}
                    step={1}
                    inputMode="numeric"
                    aria-describedby={manualCellsCorrected !== null ? undefined : 'gt-cells-corrected-hint'}
                    className="w-16 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-2 py-0.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 tabular-nums focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={displayedCellsCorrected}
                    onChange={e => {
                      const v = e.target.value;
                      if (v === '') {
                        setManualCellsCorrected(null);
                        return;
                      }
                      const n = parseInt(v, 10);
                      if (!Number.isNaN(n) && n >= 0) setManualCellsCorrected(n);
                    }}
                  />
                </label>
                {manualCellsCorrected !== null ? (
                  <button
                    type="button"
                    className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                    onClick={() => setManualCellsCorrected(null)}
                  >
                    Use automatic ({correctionCount})
                  </button>
                ) : (
                  <span id="gt-cells-corrected-hint" className="text-slate-400 dark:text-slate-500">
                    Auto from snapshot diff — edit the number to override for this session
                  </span>
                )}
              </div>
            )}
            {docLabels && !docLabelsLoading && (
              <div className="mt-3 flex flex-wrap items-end gap-3 max-w-2xl">
                <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                  Complexity tier
                  <select
                    value={docLabels.complexity_tier}
                    onChange={e =>
                      setDocLabels(prev =>
                        prev ? { ...prev, complexity_tier: e.target.value } : prev
                      )
                    }
                    className="text-xs font-normal rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="unconfirmed">Unconfirmed (required before confirm)</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </label>
                <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                  PDF type
                  <select
                    value={
                      docLabels.is_digital === null ? '' : docLabels.is_digital ? 'digital' : 'scanned'
                    }
                    onChange={e => {
                      const v = e.target.value;
                      setDocLabels(prev =>
                        prev
                          ? {
                              ...prev,
                              is_digital: v === '' ? null : v === 'digital',
                            }
                          : prev
                      );
                    }}
                    className="text-xs font-normal rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Auto (from upload heuristic)</option>
                    <option value="digital">Digital</option>
                    <option value="scanned">Scanned / OCR</option>
                  </select>
                </label>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 pb-1 max-w-xs leading-snug">
                  Tier and PDF type label this document in evaluation results. Values are detected on upload; change here
                  if they are wrong.
                </p>
              </div>
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
              {mergeUndoSurvivorId && (
                <div className="mx-3 mt-2 px-3 py-2 rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/30 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-violet-900 dark:text-violet-100">
                    Last table merge can be reverted (restores the removed table and previous rows).
                  </p>
                  <button
                    type="button"
                    disabled={isMerging}
                    onClick={() => void handleUndoMerge()}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50"
                  >
                    {isMerging ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Undo2 className="w-3.5 h-3.5" />}
                    Undo merge
                  </button>
                </div>
              )}

              <div className="flex items-center gap-2 px-3 pt-3 border-b border-slate-200 dark:border-slate-700 overflow-x-auto flex-wrap">
                {tables.map((tbl, i) => (
                  <div
                    key={tbl.id ?? `idx-${i}`}
                    className={cn(
                      'inline-flex items-center shrink-0 rounded-t border-b-2 -mb-px transition-all duration-500',
                      i === activeIdx
                        ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20'
                        : 'border-transparent',
                      tbl.id && flashSurvivorId === tbl.id
                        ? 'border-green-400 shadow-[0_0_0_2px_rgba(74,222,128,0.45)]'
                        : ''
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => setActiveIdx(i)}
                      className={cn(
                        'px-2.5 py-1.5 text-sm whitespace-nowrap',
                        i === activeIdx
                          ? 'text-indigo-700 dark:text-indigo-300 font-medium'
                          : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                      )}
                    >
                      Table {tbl.table_index + 1}
                    </button>
                    {tables.length > 1 && tbl.id && (
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation();
                          setMergingTableId(tbl.id!);
                          setMergeTargetId(null);
                          setActiveIdx(i);
                        }}
                        className="px-2 py-0.5 mr-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 border border-blue-300 dark:border-blue-600 rounded hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-colors"
                        title="Merge this table with another table"
                      >
                        Merge With →
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={e => {
                        e.stopPropagation();
                        if (mergingTableId === tbl.id) {
                          setMergingTableId(null);
                          setMergeTargetId(null);
                        }
                        deleteTableAt(i);
                      }}
                      className="p-1 mr-0.5 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                      aria-label={`Delete table ${tbl.table_index}`}
                      title="Delete table"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addTable}
                  className="ml-1 px-2 py-1 text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" /> Add table
                </button>
              </div>

              {mergingTableId && (
                <div className="mx-3 mt-2 p-3 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 text-sm">
                  <p className="text-slate-700 dark:text-slate-200 font-medium mb-2">
                    Select table to merge into this one:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {tables.filter(t => t.id && t.id !== mergingTableId).length === 0 && (
                      <p className="text-xs text-slate-500">No other saved tables to merge with.</p>
                    )}
                    {tables
                      .filter(t => t.id && t.id !== mergingTableId)
                      .map(tbl => {
                        const labelPreview = hasAutoNamedHeaders(tbl.headers)
                          ? '[unnamed columns]'
                          : tbl.headers
                              .slice(0, 3)
                              .join(', ')
                              .trim() || '…';
                        const short =
                          labelPreview.length > 72 ? `${labelPreview.slice(0, 72)}…` : labelPreview;
                        return (
                          <button
                            key={tbl.id}
                            type="button"
                            onClick={() => setMergeTargetId(tbl.id!)}
                            className={cn(
                              'px-2 py-1.5 text-xs rounded border text-left max-w-full',
                              mergeTargetId === tbl.id
                                ? 'border-indigo-500 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-100'
                                : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/80'
                            )}
                          >
                            <span className="font-medium">Table {tbl.table_index + 1}:</span>{' '}
                            {short}
                            {hasAutoNamedHeaders(tbl.headers) && (
                              <span className="ml-1 inline-flex items-center bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-200 text-[10px] rounded px-1">
                                ⚠ auto-named headers
                              </span>
                            )}
                          </button>
                        );
                      })}
                  </div>
                  {mergeTargetId && (() => {
                    const dest = tables.find(x => x.id === mergingTableId);
                    const src = tables.find(x => x.id === mergeTargetId);
                    if (!dest || !src) return null;
                    return (
                      <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-800 space-y-2">
                        <p className="text-xs text-slate-600 dark:text-slate-300">
                          Merge Table {src.table_index + 1} into Table {dest.table_index + 1} (this
                          table)? Table {dest.table_index + 1}&apos;s column headers stay exactly as
                          they are; rows from Table {src.table_index + 1} are appended and padded or
                          trimmed to match.
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={isMerging}
                            onClick={handleConfirmMerge}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                          >
                            {isMerging ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                            Confirm merge
                          </button>
                          <button
                            type="button"
                            disabled={isMerging}
                            onClick={() => {
                              setMergeTargetId(null);
                            }}
                            className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600"
                          >
                            Clear target
                          </button>
                          <button
                            type="button"
                            disabled={isMerging}
                            onClick={() => {
                              setMergingTableId(null);
                              setMergeTargetId(null);
                            }}
                            className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    );
                  })()}
                  {!mergeTargetId && (
                    <button
                      type="button"
                      className="mt-2 text-xs text-slate-600 dark:text-slate-400 hover:underline"
                      onClick={() => {
                        setMergingTableId(null);
                        setMergeTargetId(null);
                      }}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              )}

              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {t && (
                  <>
                    <div>
                      {hasAutoNamedHeaders(t.headers) && (
                        <div className="mb-2 inline-flex items-center gap-1 bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-200 text-xs rounded px-2 py-0.5">
                          <span aria-hidden>⚠</span> auto-named headers
                        </div>
                      )}
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
                      <table className="text-xs border-collapse w-max max-w-full">
                        <thead className="bg-slate-50 dark:bg-slate-800">
                          <tr>
                            <th className="w-8 px-2 py-2 border-b border-slate-200 dark:border-slate-700 text-slate-400">#</th>
                            {t.headers.map((h, ci) => (
                              <th key={ci} className="border-b border-slate-200 dark:border-slate-700 p-0 relative">
                                <div className="flex items-center min-w-0 gap-0.5">
                                  {ci === 0 && (
                                    <button
                                      type="button"
                                      title="Insert column before the first column"
                                      onClick={() => insertColumnAfter(-1)}
                                      className="shrink-0 p-1 rounded text-indigo-500 hover:text-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                                    >
                                      <Plus className="w-3 h-3" />
                                    </button>
                                  )}
                                  <input
                                    value={h}
                                    onChange={e => setHeader(ci, e.target.value)}
                                    className={cn(
                                      'min-w-[72px] max-w-[220px] flex-1 px-2 py-2 bg-transparent font-medium text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20',
                                      isCellEdited(t, -1, ci, h) && 'ring-1 ring-amber-400 dark:ring-amber-600 rounded'
                                    )}
                                  />
                                  <button
                                    type="button"
                                    title="Insert column after this one"
                                    onClick={() => insertColumnAfter(ci)}
                                    className="shrink-0 p-1 rounded text-indigo-500 hover:text-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                                  >
                                    <Plus className="w-3.5 h-3.5" />
                                  </button>
                                  {isCellEdited(t, -1, ci, h) && (
                                    <span className="absolute top-1 right-10 w-1.5 h-1.5 rounded-full bg-amber-500" title="Edited" />
                                  )}
                                  {t.headers.length > 1 && (
                                    <button
                                      type="button"
                                      title="Remove column"
                                      onClick={() => removeColumn(ci)}
                                      className="shrink-0 px-1 text-slate-300 hover:text-red-500 transition-colors"
                                    >
                                      <X className="w-3 h-3" />
                                    </button>
                                  )}
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {t.rows.map((row, ri) => {
                            const cells = padRowToLength(row, t.headers.length);
                            return (
                              <tr key={ri} className="group border-b border-slate-100 dark:border-slate-800 last:border-0">
                                <td className="px-2 py-1 text-center text-slate-300 text-[10px]">{ri + 1}</td>
                                {t.headers.map((_, ci) => {
                                  const cell = cells[ci] ?? '';
                                  return (
                                    <td key={ci} className="p-0 border-r border-slate-100 dark:border-slate-800 relative">
                                      <input
                                        value={cell}
                                        onChange={e => setCell(ri, ci, e.target.value)}
                                        className={cn(
                                          'w-full min-w-[72px] max-w-[220px] px-2 py-1.5 bg-transparent text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20',
                                          isCellEdited(t, ri, ci, cell) && 'ring-1 ring-amber-400 dark:ring-amber-600'
                                        )}
                                      />
                                      {isCellEdited(t, ri, ci, cell) && (
                                        <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-500" title="Edited" />
                                      )}
                                    </td>
                                  );
                                })}
                                <td className="px-1 w-8">
                                  <button
                                    type="button"
                                    onClick={() => removeRow(ri)}
                                    className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-red-500 transition-all"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
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
