'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import axios, { isAxiosError } from 'axios';
import {
  ArrowLeft,
  Loader2,
  Play,
  RefreshCw,
  Eye,
  AlertCircle,
  CheckCircle2,
  BarChart3,
  Pencil,
} from 'lucide-react';
import toast from 'react-hot-toast';
import TierBadge from '@/app/components/corpus/TierBadge';
import ExtractionPreviewModal from '@/app/components/evaluation/ExtractionPreviewModal';
import ExtractionEditorModal from '@/app/components/evaluation/ExtractionEditorModal';
import { ALL_EVAL_TOOLS, isExtractableTool } from '@/lib/evaluationTools';
import { sharedGetExtractionsForTool } from '@/lib/sharedExtractionsGet';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type RowKind =
  | 'pending'
  | 'extracting'
  | 'done'
  | 'no_tables'
  | 'no_tables_scanned'
  | 'api_error'
  | 'rate_limited'
  | 'failed'
  | 'evaluating'
  | 'evaluated'
  | 'eval_skipped'
  | 'eval_error';

interface Er {
  table_index: number;
  extracted_headers?: string[] | null;
  extracted_rows: string[][] | null;
  failure_reason: string | null;
  is_transient_failure: boolean;
  processing_time_ms: number | null;
  cost_usd: number | null;
  /** Server: true until Save extraction in the editor (upload Claude seed or after Extract). */
  is_draft?: boolean;
}

interface DocInfo {
  id: string;
  filename: string;
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
}

function classifyExtraction(ers: Er[], isDigital: boolean | null): RowKind {
  if (!ers.length) return 'pending';
  const first = ers[0];
  if (first.is_transient_failure) {
    if (first.failure_reason === 'rate_limit') return 'rate_limited';
    return 'api_error';
  }
  const hasData = ers.some(
    e =>
      (e.extracted_rows && e.extracted_rows.length > 0) ||
      (e.extracted_headers && e.extracted_headers.length > 0)
  );
  if (hasData) return 'done';
  if (first.failure_reason === 'tool_limitation' && isDigital === false) return 'no_tables_scanned';
  if (first.failure_reason === 'tool_limitation' || first.failure_reason === 'empty_output') return 'no_tables';
  // Permanent API / infra failures (e.g. GPT-5 400) — same retry UX as transient api_error
  if (
    first.failure_reason === 'api_error' ||
    first.failure_reason === 'timeout' ||
    first.failure_reason === 'server_down'
  ) {
    return 'api_error';
  }
  return 'failed';
}

function tableCount(ers: Er[]): number {
  return ers.length;
}

function isAbortError(e: unknown): boolean {
  return isAxiosError(e) && e.code === 'ERR_CANCELED';
}

function extractionsNeedEditorSave(ers: Er[]): boolean {
  return ers.some(e => e.is_draft === true);
}

export default function DocumentEvaluationPage() {
  const params = useParams();
  const docId = (params?.doc_id as string) ?? '';

  const [doc, setDoc] = useState<DocInfo | null>(null);
  const [rows, setRows] = useState<Record<string, { kind: RowKind; ers: Er[] }>>({});
  const [evalBlock, setEvalBlock] = useState<Record<string, { f1: number; teds: number } | null>>({});
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<{ tool: string; label: string } | null>(null);
  const [gtModal, setGtModal] = useState(false);
  const [evalMode, setEvalMode] = useState(false);
  const [extractBusy, setExtractBusy] = useState(false);
  const [evalBusy, setEvalBusy] = useState(false);
  const [retryAfter, setRetryAfter] = useState<Record<string, number>>({});
  /** After a fresh Extract (not idempotent skip), Score is blocked until Save in the editor. */
  const [pendingExtractionReview, setPendingExtractionReview] = useState<Record<string, boolean>>({});
  const [extractionEditorTool, setExtractionEditorTool] = useState<string | null>(null);
  const [extractionEditorOpen, setExtractionEditorOpen] = useState(false);

  const tickRetry = useCallback(() => {
    const now = Date.now();
    setRetryAfter(prev => {
      const next = { ...prev };
      for (const k of Object.keys(next)) {
        if (next[k] <= now) delete next[k];
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const t = setInterval(tickRetry, 1000);
    return () => clearInterval(t);
  }, [tickRetry]);

  const refreshTool = useCallback(
    async (tool: string) => {
      const { data } = await sharedGetExtractionsForTool<Er[]>(docId, tool);
      const ers = data || [];
      const kind = classifyExtraction(ers, doc?.is_digital ?? null);
      setRows(prev => ({ ...prev, [tool]: { kind, ers } }));
      setPendingExtractionReview(prev => ({
        ...prev,
        [tool]: extractionsNeedEditorSave(ers),
      }));
    },
    [docId, doc?.is_digital]
  );

  const mergeScoresIntoRows = useCallback(
    (
      prev: Record<string, { kind: RowKind; ers: Er[] }>,
      scoreKeys: string[]
    ): Record<string, { kind: RowKind; ers: Er[] }> => {
      const next = { ...prev };
      for (const tool of scoreKeys) {
        const row = next[tool];
        if (!row) continue;
        if (
          row.kind === 'done' ||
          row.kind === 'no_tables' ||
          row.kind === 'no_tables_scanned' ||
          row.kind === 'failed' ||
          row.kind === 'api_error' ||
          row.kind === 'rate_limited'
        ) {
          next[tool] = { ...row, kind: 'evaluated' };
        }
      }
      return next;
    },
    []
  );

  const refreshResults = useCallback(async () => {
    try {
      const { data } = await axios.get<
        { tool_name: string; f1_score: number | null; teds_score: number | null; table_index: number }[]
      >(`${API}/api/results/${docId}`);
      const byTool: Record<string, { f1s: number[]; teds: number[] }> = {};
      for (const r of data || []) {
        if (!byTool[r.tool_name]) byTool[r.tool_name] = { f1s: [], teds: [] };
        if (r.f1_score != null) byTool[r.tool_name].f1s.push(r.f1_score);
        if (r.teds_score != null) byTool[r.tool_name].teds.push(r.teds_score);
      }
      const out: Record<string, { f1: number; teds: number }> = {};
      for (const t of Object.keys(byTool)) {
        const { f1s, teds } = byTool[t];
        out[t] = {
          f1: f1s.length ? f1s.reduce((a, b) => a + b, 0) / f1s.length : 0,
          teds: teds.length ? teds.reduce((a, b) => a + b, 0) / teds.length : 0,
        };
      }
      setEvalBlock(out);
      setRows(prev => mergeScoresIntoRows(prev, Object.keys(out)));
    } catch {
      setEvalBlock({});
    }
  }, [docId, mergeScoresIntoRows]);

  const loadAll = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      try {
        const dRes = await axios.get<DocInfo>(`${API}/api/documents/${docId}`, { signal });
        setDoc(dRes.data);
        const nextRows: Record<string, { kind: RowKind; ers: Er[] }> = {};
        await Promise.all(
          ALL_EVAL_TOOLS.map(async ({ id }) => {
            try {
              const { data } = await axios.get<Er[]>(`${API}/api/extractions/${docId}/${id}`, {
                signal,
              });
              const kind = classifyExtraction(data || [], dRes.data.is_digital);
              nextRows[id] = { kind, ers: data || [] };
            } catch (e) {
              if (isAbortError(e)) throw e;
              nextRows[id] = { kind: 'pending', ers: [] };
            }
          })
        );
        let merged = nextRows;
        try {
          const { data } = await axios.get<
            { tool_name: string; f1_score: number | null; teds_score: number | null }[]
          >(`${API}/api/results/${docId}`, { signal });
          const byTool: Record<string, { f1s: number[]; teds: number[] }> = {};
          for (const r of data || []) {
            if (!byTool[r.tool_name]) byTool[r.tool_name] = { f1s: [], teds: [] };
            if (r.f1_score != null) byTool[r.tool_name].f1s.push(r.f1_score);
            if (r.teds_score != null) byTool[r.tool_name].teds.push(r.teds_score);
          }
          const out: Record<string, { f1: number; teds: number }> = {};
          for (const t of Object.keys(byTool)) {
            const { f1s, teds } = byTool[t];
            out[t] = {
              f1: f1s.length ? f1s.reduce((a, b) => a + b, 0) / f1s.length : 0,
              teds: teds.length ? teds.reduce((a, b) => a + b, 0) / teds.length : 0,
            };
          }
          setEvalBlock(out);
          merged = mergeScoresIntoRows(nextRows, Object.keys(out));
        } catch (e) {
          if (isAbortError(e)) throw e;
          setEvalBlock({});
        }
        setRows(merged);
        const pendingInit: Record<string, boolean> = {};
        for (const { id } of ALL_EVAL_TOOLS) {
          pendingInit[id] = extractionsNeedEditorSave(merged[id]?.ers ?? []);
        }
        setPendingExtractionReview(pendingInit);
      } catch (e) {
        if (isAbortError(e)) return;
        setDoc(null);
        setRows({});
        setPendingExtractionReview({});
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
        }
      }
    },
    [docId, mergeScoresIntoRows]
  );

  useEffect(() => {
    if (!docId) return;
    const ac = new AbortController();
    void loadAll(ac.signal);
    return () => ac.abort();
  }, [loadAll, docId]);

  const openExtractionEditor = (tool: string) => {
    setExtractionEditorTool(tool);
    setExtractionEditorOpen(true);
  };

  const runExtract = async (tool: string, opts?: { force?: boolean }) => {
    if (!doc || !docId || extractBusy) return;
    setExtractBusy(true);
    setRows(prev => ({
      ...prev,
      [tool]: { ...prev[tool], kind: 'extracting', ers: prev[tool]?.ers || [] },
    }));
    try {
      const { data } = await axios.post<{
        failure_reason?: string | null;
        is_transient_failure?: boolean;
        already_exists?: boolean;
        /** True when the server actually invoked the extractor (Extract, Re-run, Retry). */
        extraction_executed?: boolean;
      }>(`${API}/api/extract/${docId}/${tool}`, null, {
        params: opts?.force ? { force: true } : undefined,
      });
      if (data.failure_reason === 'rate_limit' || data.is_transient_failure) {
        setRetryAfter(prev => ({ ...prev, [tool]: Date.now() + 60_000 }));
      }
      const openedNewRun =
        data.extraction_executed === true ||
        (data.extraction_executed == null && data.already_exists === false);
      await refreshTool(tool);
      if (openedNewRun) {
        setExtractionEditorTool(tool);
        setExtractionEditorOpen(true);
      }
    } catch (e: unknown) {
      const ax = e as { response?: { status?: number } };
      if (ax.response?.status === 429) {
        setRetryAfter(prev => ({ ...prev, [tool]: Date.now() + 60_000 }));
      }
      toast.error('Extraction request failed');
      await refreshTool(tool);
    } finally {
      setExtractBusy(false);
    }
  };

  const runEvaluateOne = async (tool: string) => {
    if (!docId || evalBusy || extractBusy) return;
    if (pendingExtractionReview[tool]) {
      toast.error('Save extraction in the editor before scoring');
      return;
    }
    const r = rows[tool];
    if (!r || !r.ers.length) {
      toast.error('No extraction to evaluate');
      return;
    }
    setEvalBusy(true);
    setRows(prev => ({
      ...prev,
      [tool]: { ...prev[tool], kind: 'evaluating', ers: prev[tool]?.ers || [] },
    }));
    try {
      await axios.post(`${API}/api/evaluate-tool/${docId}/${tool}`);
      await refreshTool(tool);
      await refreshResults();
      setRows(prev => ({
        ...prev,
        [tool]: { ...prev[tool], kind: 'evaluated', ers: prev[tool]?.ers || [] },
      }));
      toast.success(`Evaluated ${tool}`);
    } catch (e: unknown) {
      const ax = e as { response?: { status?: number; data?: unknown } };
      if (ax.response?.status === 422) {
        const body = ax.response?.data as { error?: string; message?: string } | undefined;
        if (body?.error === 'draft_extraction') {
          toast.error(body?.message ?? 'Save extraction in the editor before scoring');
        } else {
          setGtModal(true);
        }
        await refreshTool(tool);
      } else if (ax.response?.status === 503) {
        toast.error('Transient extraction failure — fix extraction before scoring');
        await refreshTool(tool);
      } else {
        toast.error('Evaluation failed');
        setRows(prev => ({
          ...prev,
          [tool]: { ...prev[tool], kind: 'eval_error', ers: prev[tool]?.ers || [] },
        }));
      }
    } finally {
      setEvalBusy(false);
    }
  };

  const evaluateAll = async () => {
    if (!docId || evalBusy || extractBusy) return;
    setEvalMode(true);
    setEvalBusy(true);
    let stopped = false;
    for (const { id } of ALL_EVAL_TOOLS) {
      if (pendingExtractionReview[id]) continue;
      const r = rows[id];
      if (!r || r.kind === 'pending' || r.kind === 'extracting') {
        continue;
      }
      if (!r.ers.length) continue;
      const kindBeforeEval = r.kind;
      setRows(prev => ({
        ...prev,
        [id]: { ...prev[id], kind: 'evaluating', ers: prev[id]?.ers || [] },
      }));
      try {
        await axios.post(`${API}/api/evaluate-tool/${docId}/${id}`);
        setRows(prev => ({
          ...prev,
          [id]: { ...prev[id], kind: 'evaluated', ers: prev[id]?.ers || [] },
        }));
      } catch (e: unknown) {
        const ax = e as { response?: { status?: number; data?: unknown } };
        if (ax.response?.status === 422) {
          const body = ax.response?.data as { error?: string; message?: string } | undefined;
          if (body?.error === 'draft_extraction') {
            toast.error(body?.message ?? 'Save extraction in the editor before scoring');
            setRows(prev => ({
              ...prev,
              [id]: { ...prev[id], kind: kindBeforeEval, ers: prev[id]?.ers || [] },
            }));
            continue;
          } else {
            setGtModal(true);
            stopped = true;
            break;
          }
        }
        if (ax.response?.status === 503) {
          setRows(prev => ({
            ...prev,
            [id]: { ...prev[id], kind: 'eval_skipped', ers: prev[id]?.ers || [] },
          }));
          continue;
        }
        setRows(prev => ({
          ...prev,
          [id]: { ...prev[id], kind: 'eval_error', ers: prev[id]?.ers || [] },
        }));
      }
    }
    await refreshResults();
    if (!stopped) toast.success('Evaluation finished');
    setEvalMode(false);
    setEvalBusy(false);
  };

  const renderStatus = (tool: string) => {
    const r = rows[tool];
    if (!r) return <span className="text-slate-400 text-xs">—</span>;
    const k = r.kind;
    const n = tableCount(r.ers);
    const fr = r.ers[0]?.failure_reason;
    const needsSave = Boolean(pendingExtractionReview[tool]);

    if (k === 'pending')
      return <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 dark:bg-slate-800">Not run</span>;
    if (k === 'extracting')
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/40">
          <Loader2 className="w-3 h-3 animate-spin" />
          Extracting…
        </span>
      );
    if (k === 'done')
      return (
        <div className="flex flex-col gap-0.5 items-start">
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40">
            Success ({n} tables)
          </span>
          {needsSave && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 dark:bg-amber-900/40">
              Save extraction to enable scoring
            </span>
          )}
          {!needsSave && n > 0 && (
            <span className="text-[10px] text-slate-500">Extraction ready</span>
          )}
        </div>
      );
    if (k === 'no_tables' || k === 'no_tables_scanned')
      return (
        <div className="flex flex-col gap-0.5 items-start">
          <span
            className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-900 dark:bg-amber-900/40 cursor-help"
            title={
              k === 'no_tables_scanned'
                ? 'Rule-based tools cannot process image-based PDFs'
                : 'Tool ran but returned no table structure'
            }
          >
            No tables{k === 'no_tables_scanned' ? ' (scanned)' : ''}
          </span>
          {needsSave && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 dark:bg-amber-900/40">
              Save extraction to enable scoring
            </span>
          )}
        </div>
      );
    if (k === 'rate_limited') {
      const until = retryAfter[tool];
      const left = until ? Math.max(0, Math.ceil((until - Date.now()) / 1000)) : 0;
      return (
        <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/40" title="Rate limited">
          Rate limited{left > 0 ? ` (${left}s)` : ''}
        </span>
      );
    }
    if (k === 'api_error')
      return (
        <span
          className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/40 cursor-help"
          title={`Failed: ${fr || 'transient'}`}
        >
          Failed (API)
        </span>
      );
    if (k === 'failed')
      return (
        <span className="text-xs px-2 py-0.5 rounded bg-red-950 text-red-100 dark:bg-red-950 cursor-help" title="Processing failed">
          Failed
        </span>
      );
    if (k === 'evaluating')
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">
          <Loader2 className="w-3 h-3 animate-spin" />
          Scoring…
        </span>
      );
    if (k === 'evaluated') {
      const ev = evalBlock[tool];
      return (
        <div className="flex flex-col gap-0.5 items-start">
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Scored
          </span>
          {ev && (
            <span className="text-[10px] text-slate-500">
              F1 {ev.f1.toFixed(3)} · TEDS {ev.teds.toFixed(3)}
            </span>
          )}
        </div>
      );
    }
    if (k === 'eval_skipped')
      return <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-900">Skipped (transient extraction)</span>;
    if (k === 'eval_error') return <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800">Score error</span>;

    return <span className="text-xs text-slate-400">—</span>;
  };

  if (!docId) {
    return <div className="max-w-3xl mx-auto px-4 py-16 text-center text-slate-500">Invalid document.</div>;
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const documentReady = Boolean(doc);
  const canExtract = documentReady && !extractBusy && !evalMode && !evalBusy;

  const allExtractionsComplete = ALL_EVAL_TOOLS.every(({ id }) => {
    const k = rows[id]?.kind;
    return k && k !== 'pending' && k !== 'extracting';
  });

  const toolsReadyToScore = ALL_EVAL_TOOLS.filter(({ id }) => {
    const r = rows[id];
    return (
      r &&
      r.ers.length > 0 &&
      r.kind !== 'pending' &&
      r.kind !== 'extracting' &&
      !pendingExtractionReview[id]
    );
  }).length;

  const anyPendingReview = ALL_EVAL_TOOLS.some(({ id }) => pendingExtractionReview[id]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col gap-2">
        <Link
          href="/corpus"
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1 w-fit"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Corpus
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{doc?.filename ?? 'Document unavailable'}</h1>
          {doc && (
            <TierBadge tier={doc.complexity_tier as 'low' | 'medium' | 'high' | 'unconfirmed'} />
          )}
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Claude runs on upload as a draft extraction: open Draft on the evaluation page, adjust tables if needed, and save before scoring. Run other tools, confirm ground truth in Corpus, then score against confirmed tables.
        </p>
        {!documentReady && (
          <p className="text-sm text-amber-700 dark:text-amber-300 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 px-3 py-2">
            No file on disk — open this document from{' '}
            <Link href="/corpus" className="font-medium underline">
              Corpus
            </Link>
            .
          </p>
        )}
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="text-left px-4 py-3">Tool</th>
              <th className="text-left px-4 py-3">Generation</th>
              <th className="text-left px-4 py-3">Extraction</th>
              <th className="text-center px-4 py-3">Tables</th>
              <th className="text-right px-4 py-3">Time (ms)</th>
              <th className="text-right px-4 py-3">Cost</th>
              <th className="text-right px-4 py-3">Extract</th>
              <th className="text-right px-4 py-3">Score</th>
            </tr>
          </thead>
          <tbody>
            {ALL_EVAL_TOOLS.map(({ id, label, gen }) => {
              const r = rows[id];
              const n = r ? tableCount(r.ers) : 0;
              const ms = r ? Math.max(...r.ers.map(e => e.processing_time_ms || 0), 0) : 0;
              const cost = r ? r.ers.reduce((s, e) => s + (e.cost_usd || 0), 0) : 0;
              const k = r?.kind || 'pending';
              const retryWait =
                retryAfter[id] && retryAfter[id] > Date.now()
                  ? Math.ceil((retryAfter[id] - Date.now()) / 1000)
                  : 0;
              const extractable = isExtractableTool(id);
              const canPreview =
                k === 'done' ||
                k === 'no_tables' ||
                k === 'no_tables_scanned' ||
                k === 'evaluated' ||
                k === 'api_error' ||
                k === 'rate_limited' ||
                k === 'failed';
              const canScoreThis =
                r &&
                r.ers.length > 0 &&
                k !== 'pending' &&
                k !== 'extracting' &&
                k !== 'evaluating' &&
                !pendingExtractionReview[id];
              const canEditExtraction =
                documentReady &&
                r &&
                r.ers.length > 0 &&
                k !== 'pending' &&
                k !== 'extracting' &&
                k !== 'evaluating';
              const needsEditorSave = Boolean(pendingExtractionReview[id]);

              return (
                <tr key={id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">
                    {label}
                    {!extractable && (
                      <span className="block text-[10px] font-normal text-slate-400 mt-0.5">Seeded on upload</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{gen}</td>
                  <td className="px-4 py-3">{renderStatus(id)}</td>
                  <td className="px-4 py-3 text-center tabular-nums">{n}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-600">{ms || '—'}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-600">{cost ? `$${cost.toFixed(4)}` : '—'}</td>
                  <td className="px-4 py-3 text-right">
                    {!extractable ? (
                      <div className="flex flex-wrap justify-end gap-1">
                        {canEditExtraction && (
                          <button
                            type="button"
                            disabled={!documentReady || extractBusy}
                            onClick={() => openExtractionEditor(id)}
                            className={
                              needsEditorSave
                                ? 'inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100 hover:bg-amber-100 dark:hover:bg-amber-900/50'
                                : 'inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
                            }
                          >
                            <Pencil className="w-3 h-3" />
                            {needsEditorSave ? 'Draft' : 'Edit'}
                          </button>
                        )}
                        {!canEditExtraction && <span className="text-xs text-slate-400">—</span>}
                      </div>
                    ) : (
                      <div className="flex flex-wrap justify-end gap-1">
                        {k === 'pending' && (
                          <button
                            type="button"
                            disabled={!canExtract}
                            onClick={() => runExtract(id)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40"
                          >
                            <Play className="w-3 h-3" />
                            Extract
                          </button>
                        )}
                        {(k === 'done' || k === 'no_tables' || k === 'no_tables_scanned' || k === 'evaluated') && !evalMode && (
                          <>
                            {canEditExtraction && (
                              <button
                                type="button"
                                disabled={!documentReady || extractBusy}
                                onClick={() => openExtractionEditor(id)}
                                className={
                                  needsEditorSave
                                    ? 'inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100 hover:bg-amber-100 dark:hover:bg-amber-900/50'
                                    : 'inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40'
                                }
                              >
                                <Pencil className="w-3 h-3" />
                                {needsEditorSave ? 'Draft' : 'Edit'}
                              </button>
                            )}
                            {canPreview && (
                              <button
                                type="button"
                                disabled={!documentReady}
                                onClick={() => documentReady && setPreview({ tool: id, label })}
                                className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
                              >
                                <Eye className="w-3 h-3" />
                                Preview
                              </button>
                            )}
                            <button
                              type="button"
                              disabled={!documentReady || extractBusy}
                              onClick={() => runExtract(id, { force: true })}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-200 dark:border-slate-600 hover:bg-slate-50"
                            >
                              <RefreshCw className="w-3 h-3" />
                              Re-run
                            </button>
                          </>
                        )}
                        {(k === 'api_error' || k === 'rate_limited' || k === 'failed') && !evalMode && (
                          <>
                            {canEditExtraction && (
                              <button
                                type="button"
                                disabled={!documentReady || extractBusy}
                                onClick={() => openExtractionEditor(id)}
                                className={
                                  needsEditorSave
                                    ? 'inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100 hover:bg-amber-100 dark:hover:bg-amber-900/50'
                                    : 'inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-200 dark:border-slate-600 hover:bg-slate-50'
                                }
                              >
                                <Pencil className="w-3 h-3" />
                                {needsEditorSave ? 'Draft' : 'Edit'}
                              </button>
                            )}
                            <button
                              type="button"
                              disabled={!documentReady || extractBusy || retryWait > 0}
                              onClick={() => runExtract(id, { force: true })}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-40"
                            >
                              <RefreshCw className="w-3 h-3" />
                              Retry{retryWait > 0 ? ` (${retryWait}s)` : ''}
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {canScoreThis ? (
                      <button
                        type="button"
                        disabled={evalBusy || extractBusy || evalMode}
                        onClick={() => runEvaluateOne(id)}
                        className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-40"
                      >
                        <BarChart3 className="w-3 h-3" />
                        Score
                      </button>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-2">
        <div className="flex flex-wrap gap-3">
          <Link
            href="/corpus"
            className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-center text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            ← Corpus
          </Link>
          <Link
            href={`/results/${docId}`}
            className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-center text-indigo-600 dark:text-indigo-400 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            Detailed results
          </Link>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            disabled={
              !documentReady ||
              !allExtractionsComplete ||
              extractBusy ||
              evalMode ||
              evalBusy ||
              anyPendingReview
            }
            onClick={evaluateAll}
            className="px-4 py-2 text-sm rounded-lg bg-violet-600 hover:bg-violet-700 text-white font-medium disabled:opacity-40"
          >
            {allExtractionsComplete && !anyPendingReview
              ? `Score all tools (${toolsReadyToScore} ready)`
              : anyPendingReview
                ? 'Save all new extractions before scoring'
                : 'Complete all extractions first'}
          </button>
          {!allExtractionsComplete && (
            <p className="text-xs text-slate-500 text-right max-w-xs">
              Run Extract on each tool above (Claude is seeded from upload — open Draft and save when ready).
            </p>
          )}
          {allExtractionsComplete && anyPendingReview && (
            <p className="text-xs text-amber-700 dark:text-amber-300 text-right max-w-xs">
              Open each tool flagged “Save extraction…” and click Save extraction in the editor.
            </p>
          )}
        </div>
      </div>

      {preview && doc && (
        <ExtractionPreviewModal
          docId={docId}
          filename={doc.filename}
          toolName={preview.tool}
          toolLabel={preview.label}
          onClose={() => setPreview(null)}
        />
      )}

      {extractionEditorTool && (
        <ExtractionEditorModal
          docId={docId}
          toolName={extractionEditorTool}
          toolLabel={ALL_EVAL_TOOLS.find(t => t.id === extractionEditorTool)?.label ?? extractionEditorTool}
          isOpen={extractionEditorOpen}
          onClose={() => {
            setExtractionEditorOpen(false);
            setExtractionEditorTool(null);
          }}
          onSaved={() => {
            const t = extractionEditorTool;
            if (t) void refreshTool(t);
            void refreshResults();
          }}
        />
      )}

      {gtModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-slate-700 dark:text-slate-200">
                No confirmed ground truth for this document. Open Corpus, edit ground truth, and confirm tables first.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setGtModal(false);
                window.location.href = '/corpus';
              }}
              className="w-full py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium"
            >
              Go to Corpus
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
