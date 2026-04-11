'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';
import {
  ArrowLeft,
  Loader2,
  Play,
  RefreshCw,
  Eye,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';
import TierBadge from '@/app/components/corpus/TierBadge';
import ExtractionPreviewModal from '@/app/components/evaluation/ExtractionPreviewModal';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const TOOLS = [
  { id: 'pymupdf', label: 'PyMuPDF', gen: 'Rule-based' },
  { id: 'docling', label: 'Docling', gen: 'Computer Vision' },
  { id: 'google_docai', label: 'Google DocAI', gen: 'Computer Vision' },
  { id: 'gpt5', label: 'GPT-5 Vision', gen: 'LLM' },
  { id: 'claude_sonnet', label: 'Claude Sonnet', gen: 'LLM' },
  { id: 'mistral', label: 'Mistral AI', gen: 'LLM' },
] as const;

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
  extracted_rows: string[][] | null;
  failure_reason: string | null;
  is_transient_failure: boolean;
  processing_time_ms: number | null;
  cost_usd: number | null;
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
  const hasData = ers.some(e => e.extracted_rows && e.extracted_rows.length > 0);
  if (hasData) return 'done';
  if (first.failure_reason === 'tool_limitation' && isDigital === false) return 'no_tables_scanned';
  if (first.failure_reason === 'tool_limitation' || first.failure_reason === 'empty_output') return 'no_tables';
  return 'failed';
}

function tableCount(ers: Er[]): number {
  return ers.filter(e => e.extracted_rows && e.extracted_rows.length > 0).length;
}

export default function DocumentEvaluationPage() {
  const params = useParams();
  const router = useRouter();
  const docId = (params?.doc_id as string) ?? '';

  const [doc, setDoc] = useState<DocInfo | null>(null);
  const [rows, setRows] = useState<Record<string, { kind: RowKind; ers: Er[] }>>({});
  const [evalBlock, setEvalBlock] = useState<Record<string, { f1: number; teds: number } | null>>({});
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<{ tool: string; label: string } | null>(null);
  const [gtModal, setGtModal] = useState(false);
  const [evalMode, setEvalMode] = useState(false);
  const [evalBanner, setEvalBanner] = useState(false);
  const [retryAfter, setRetryAfter] = useState<Record<string, number>>({});

  const [extractBusy, setExtractBusy] = useState(false);

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
      const { data } = await axios.get<Er[]>(`${API}/api/extractions/${docId}/${tool}`);
      const kind = classifyExtraction(data || [], doc?.is_digital ?? null);
      setRows(prev => ({ ...prev, [tool]: { kind, ers: data || [] } }));
    },
    [docId, doc?.is_digital]
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
    } catch {
      setEvalBlock({});
    }
  }, [docId]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const dRes = await axios.get<DocInfo>(`${API}/api/documents/${docId}`);
      setDoc(dRes.data);
      const nextRows: Record<string, { kind: RowKind; ers: Er[] }> = {};
      await Promise.all(
        TOOLS.map(async ({ id }) => {
          try {
            const { data } = await axios.get<Er[]>(`${API}/api/extractions/${docId}/${id}`);
            const kind = classifyExtraction(data || [], dRes.data.is_digital);
            nextRows[id] = { kind, ers: data || [] };
          } catch {
            nextRows[id] = { kind: 'pending', ers: [] };
          }
        })
      );
      setRows(nextRows);
      await refreshResults();
    } catch {
      setDoc(null);
      setRows({});
    } finally {
      setLoading(false);
    }
  }, [docId, refreshResults]);

  useEffect(() => {
    if (!docId) return;
    loadAll();
  }, [loadAll, docId]);

  const runExtract = async (tool: string) => {
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
        tables_extracted?: number;
      }>(`${API}/api/extract/${docId}/${tool}`);
      if (data.failure_reason === 'rate_limit' || data.is_transient_failure) {
        setRetryAfter(prev => ({ ...prev, [tool]: Date.now() + 60_000 }));
      }
      await refreshTool(tool);
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

  const allExtractionsComplete = TOOLS.every(({ id }) => {
    const k = rows[id]?.kind;
    return k && k !== 'pending' && k !== 'extracting';
  });

  const evaluateAll = async () => {
    if (!doc || !docId) return;
    setEvalMode(true);
    for (const { id } of TOOLS) {
      setRows(prev => ({
        ...prev,
        [id]: { ...prev[id], kind: 'evaluating', ers: prev[id]?.ers || [] },
      }));
      try {
        const res = await axios.post(`${API}/api/evaluate-tool/${docId}/${id}`);
        if (res.status === 200) {
          setRows(prev => ({
            ...prev,
            [id]: { ...prev[id], kind: 'evaluated', ers: prev[id]?.ers || [] },
          }));
        }
      } catch (e: unknown) {
        const ax = e as { response?: { status?: number; data?: { error?: string } } };
        if (ax.response?.status === 422) {
          setGtModal(true);
          setEvalMode(false);
          return;
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
    setEvalMode(false);
    setEvalBanner(true);
    setTimeout(() => {
      router.push(`/results/${docId}`);
    }, 2000);
  };

  const renderStatus = (tool: string) => {
    const r = rows[tool];
    if (!r) return <span className="text-slate-400 text-xs">—</span>;
    const k = r.kind;
    const n = tableCount(r.ers);
    const ms = Math.max(...r.ers.map(e => e.processing_time_ms || 0), 0);
    const cost = r.ers.reduce((s, e) => s + (e.cost_usd || 0), 0);
    const fr = r.ers[0]?.failure_reason;

    if (k === 'pending')
      return <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 dark:bg-slate-800">Pending</span>;
    if (k === 'extracting')
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/40">
          <Loader2 className="w-3 h-3 animate-spin" />
          Extracting…
        </span>
      );
    if (k === 'done')
      return (
        <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40">
          Done ({n})
        </span>
      );
    if (k === 'no_tables' || k === 'no_tables_scanned')
      return (
        <span
          className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-900 dark:bg-amber-900/40 cursor-help"
          title={
            k === 'no_tables_scanned'
              ? 'Rule-based tools cannot process image-based PDFs'
              : 'Tool ran but returned no table structure'
          }
        >
          No Tables{ k === 'no_tables_scanned' ? ' (scanned)' : ''}
        </span>
      );
    if (k === 'rate_limited') {
      const until = retryAfter[tool];
      const left = until ? Math.max(0, Math.ceil((until - Date.now()) / 1000)) : 0;
      return (
        <span
          className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/40"
          title="Rate limited — wait before retry"
        >
          Rate Limited{left > 0 ? ` (${left}s)` : ''}
        </span>
      );
    }
    if (k === 'api_error')
      return (
        <span
          className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/40 cursor-help"
          title={`Failed due to: ${fr || 'transient'}. Retrying may succeed.`}
        >
          API Error
        </span>
      );
    if (k === 'failed')
      return (
        <span
          className="text-xs px-2 py-0.5 rounded bg-red-950 text-red-100 dark:bg-red-950 cursor-help"
          title="This tool could not process this document type."
        >
          Failed
        </span>
      );
    if (k === 'evaluating')
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">
          <Loader2 className="w-3 h-3 animate-spin" />
          Evaluating…
        </span>
      );
    if (k === 'evaluated') {
      const ev = evalBlock[tool];
      return (
        <div className="flex flex-col gap-0.5 items-start">
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Evaluated ✓
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
      return (
        <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-900">Skipped — API error</span>
      );
    if (k === 'eval_error')
      return <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800">Evaluation error</span>;

    return <span className="text-xs text-slate-400">—</span>;
  };

  if (!docId) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-slate-500">Invalid document.</div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  /** PDF / DB record loaded successfully — enables Run, Retry, and Evaluate All. */
  const documentReady = Boolean(doc);
  const canExtract = documentReady && !extractBusy && !evalMode;

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
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            {doc?.filename ?? 'Document unavailable'}
          </h1>
          {doc && <TierBadge tier={doc.complexity_tier as 'low' | 'medium' | 'high'} />}
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">Run each tool, then evaluate all</p>
        {!documentReady && (
          <p className="text-sm text-amber-700 dark:text-amber-300 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 px-3 py-2">
            No file loaded for this document (missing or deleted). Run and evaluate actions are disabled — open a document from{' '}
            <Link href="/corpus" className="font-medium underline">
              Corpus
            </Link>
            .
          </p>
        )}
      </div>

      {evalBanner && (
        <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 px-4 py-3 text-sm text-emerald-900 dark:text-emerald-200">
          Evaluation complete. Redirecting to results…
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="text-left px-4 py-3">Tool</th>
              <th className="text-left px-4 py-3">Generation</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-center px-4 py-3">Tables</th>
              <th className="text-right px-4 py-3">Time</th>
              <th className="text-right px-4 py-3">Cost</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {TOOLS.map(({ id, label, gen }) => {
              const r = rows[id];
              const n = r ? tableCount(r.ers) : 0;
              const ms = r ? Math.max(...r.ers.map(e => e.processing_time_ms || 0), 0) : 0;
              const cost = r ? r.ers.reduce((s, e) => s + (e.cost_usd || 0), 0) : 0;
              const k = r?.kind || 'pending';
              const retryWait =
                retryAfter[id] && retryAfter[id] > Date.now()
                  ? Math.ceil((retryAfter[id] - Date.now()) / 1000)
                  : 0;

              return (
                <tr key={id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{label}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{gen}</td>
                  <td className="px-4 py-3">{renderStatus(id)}</td>
                  <td className="px-4 py-3 text-center tabular-nums">{n}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-600">{ms ? `${ms}` : '—'}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-600">
                    {cost ? `$${cost.toFixed(4)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-wrap justify-end gap-1">
                      {k === 'pending' && (
                        <button
                          type="button"
                          disabled={!canExtract}
                          onClick={() => runExtract(id)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <Play className="w-3 h-3" />
                          Run
                        </button>
                      )}
                      {(k === 'done' || k === 'no_tables' || k === 'no_tables_scanned') && !evalMode && (
                        <>
                          <button
                            type="button"
                            disabled={!documentReady}
                            onClick={() => documentReady && setPreview({ tool: id, label })}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <Eye className="w-3 h-3" />
                            Preview
                          </button>
                          <button
                            type="button"
                            disabled={!documentReady || extractBusy}
                            onClick={() => runExtract(id)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <RefreshCw className="w-3 h-3" />
                            Retry
                          </button>
                        </>
                      )}
                      {(k === 'api_error' || k === 'rate_limited') && !evalMode && (
                        <button
                          type="button"
                          disabled={!documentReady || extractBusy || retryWait > 0}
                          onClick={() => runExtract(id)}
                          title={`Failed due to: ${r?.ers[0]?.failure_reason || 'transient'}. This is a transient error — retrying may succeed.`}
                          className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <RefreshCw className="w-3 h-3" />
                          Retry{retryWait > 0 ? ` (${retryWait}s)` : ''}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-2">
        <Link
          href="/corpus"
          className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-center text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          ← Back to Corpus
        </Link>
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            disabled={!documentReady || !allExtractionsComplete || extractBusy || evalMode}
            onClick={evaluateAll}
            className="px-4 py-2 text-sm rounded-lg bg-violet-600 hover:bg-violet-700 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {allExtractionsComplete
              ? `Evaluate All Tools (${TOOLS.length} tools ready)`
              : 'Evaluate All Tools →'}
          </button>
          {!allExtractionsComplete && (
            <p className="text-xs text-slate-500">Run all tool extractions above to enable evaluation</p>
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

      {gtModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-slate-700 dark:text-slate-200">
                This document has no confirmed ground truth. Go back to corpus and complete annotation first.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setGtModal(false);
                router.push('/corpus');
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
