'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import axios, { isAxiosError } from 'axios';
import { Loader2, Download, ArrowLeft } from 'lucide-react';
import TierBadge from '@/app/components/corpus/TierBadge';
import { sharedGetExtractionsForTool } from '@/lib/sharedExtractionsGet';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const TOOLS = [
  { id: 'pymupdf', label: 'PyMuPDF', gen: 'Rule-based' },
  { id: 'docling', label: 'Docling', gen: 'Computer Vision' },
  { id: 'aws_textract', label: 'AWS Textract', gen: 'Computer Vision' },
  { id: 'google_docai', label: 'Google DocAI', gen: 'Computer Vision' },
  { id: 'gpt5', label: 'GPT-5 Vision', gen: 'LLM' },
  { id: 'claude_sonnet', label: 'Claude Sonnet', gen: 'LLM' },
  { id: 'mistral', label: 'Mistral AI', gen: 'LLM' },
] as const;

interface DocInfo {
  id: string;
  filename: string;
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
}

interface ScoreRow {
  tool_name: string;
  table_index: number;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  teds_score: number | null;
  grits_top: number | null;
  grits_con: number | null;
  grits_loc: number | null;
  processing_time_ms: number | null;
  cost_usd: number | null;
  error?: string | null;
  failure_reason?: string | null;
  is_transient_failure?: boolean;
}

interface Er {
  failure_reason: string | null;
  is_transient_failure: boolean;
}

function avg(nums: (number | null | undefined)[]): number | null {
  const xs = nums.filter((x): x is number => x != null);
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
}

function isAbortError(e: unknown): boolean {
  return isAxiosError(e) && e.code === 'ERR_CANCELED';
}

export default function DocumentResultsPage() {
  const params = useParams();
  const docId = (params?.doc_id as string) ?? '';

  const [doc, setDoc] = useState<DocInfo | null>(null);
  const [scores, setScores] = useState<ScoreRow[]>([]);
  const [ers, setErs] = useState<Record<string, Er[]>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      try {
        const [dRes, sRes, ...extRes] = await Promise.all([
          axios.get<DocInfo>(`${API}/api/documents/${docId}`, { signal }),
          axios.get<ScoreRow[]>(`${API}/api/results/${docId}`, { signal }),
          ...TOOLS.map(t =>
            sharedGetExtractionsForTool<Er[]>(docId, t.id, { signal }).catch(e => {
              if (isAbortError(e)) throw e;
              return { data: [] as Er[] };
            })
          ),
        ]);
        setDoc(dRes.data);
        setScores(sRes.data || []);
        const erMap: Record<string, Er[]> = {};
        TOOLS.forEach((t, i) => {
          erMap[t.id] = (extRes[i] as { data: Er[] }).data || [];
        });
        setErs(erMap);
      } catch (e) {
        if (isAbortError(e)) return;
        setDoc(null);
        setScores([]);
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
        }
      }
    },
    [docId]
  );

  useEffect(() => {
    if (!docId) return;
    const ac = new AbortController();
    void load(ac.signal);
    return () => ac.abort();
  }, [load, docId]);

  const tableRows = useMemo(() => {
    return TOOLS.map(({ id, label, gen }) => {
      const toolScores = scores.filter(s => s.tool_name === id);
      const ext = ers[id] || [];
      const firstEr = ext[0];
      const transient = firstEr?.is_transient_failure;
      const fr = firstEr?.failure_reason;

      const scoredZero =
        toolScores.length > 0 &&
        toolScores.some(
          s => s.failure_reason === 'tool_limitation' || s.failure_reason === 'empty_output'
        );

      const a = {
        tool: id,
        label,
        gen,
        precision: avg(toolScores.map(s => s.precision)),
        recall: avg(toolScores.map(s => s.recall)),
        f1: avg(toolScores.map(s => s.f1_score)),
        teds: avg(toolScores.map(s => s.teds_score)),
        gt: avg(toolScores.map(s => s.grits_top)),
        gc: avg(toolScores.map(s => s.grits_con)),
        timeMs: Math.max(...toolScores.map(s => s.processing_time_ms || 0), 0) || null,
        cost: toolScores.reduce((s, x) => s + (x.cost_usd || 0), 0) || null,
        transient,
        failureReason: fr,
        hasScores: toolScores.length > 0,
        scoredZero,
      };
      return a;
    }).sort((a, b) => (b.f1 ?? -1) - (a.f1 ?? -1));
  }, [scores, ers]);

  const exportDoc = () => {
    window.open(`${API}/api/results/export/csv?doc_id=${encodeURIComponent(docId)}`, '_blank');
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

  if (!doc) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-slate-500">
        Document not found.
        <Link href="/corpus" className="block mt-4 text-indigo-600 hover:underline">
          Back to Corpus
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <Link
        href={`/evaluation/${docId}`}
        className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Evaluation
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{doc.filename}</h1>
          <TierBadge tier={doc.complexity_tier as 'low' | 'medium' | 'high' | 'unconfirmed'} />
          <span className="text-sm text-slate-500">{doc.page_count ?? '—'} pages</span>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded ${
              doc.is_digital === true
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30'
                : 'bg-orange-100 text-orange-800 dark:bg-orange-900/30'
            }`}
          >
            {doc.is_digital === true ? 'Digital' : doc.is_digital === false ? 'Scanned' : 'Type unknown'}
          </span>
        </div>
        <button
          type="button"
          onClick={exportDoc}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
        >
          <Download className="w-4 h-4" />
          Save Results
        </button>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm min-w-[900px]">
          <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="text-left px-3 py-2">Tool</th>
              <th className="text-left px-3 py-2">Generation</th>
              <th className="text-right px-3 py-2">F1</th>
              <th className="text-right px-3 py-2">Precision</th>
              <th className="text-right px-3 py-2">Recall</th>
              <th className="text-right px-3 py-2">TEDS</th>
              <th className="text-right px-3 py-2">GriTS-Top</th>
              <th className="text-right px-3 py-2">GriTS-Con</th>
              <th className="text-right px-3 py-2">Time (ms)</th>
              <th className="text-right px-3 py-2">Cost ($)</th>
              <th className="text-left px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map(row => {
              let status: ReactNode;
              if (row.transient && !row.hasScores) {
                status = (
                  <span
                    className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 cursor-help"
                    title="API failures are excluded from accuracy analysis as they reflect infrastructure issues, not tool capability."
                  >
                    Not scored — transient failure
                  </span>
                );
              } else if (row.scoredZero && row.hasScores) {
                status = (
                  <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-900">Scored as 0 — no output</span>
                );
              } else if (row.hasScores) {
                status = <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">Scored</span>;
              } else {
                status = <span className="text-xs text-slate-400">—</span>;
              }

              const fmt = (v: number | null) => (v != null ? v.toFixed(4) : '—');

              return (
                <tr key={row.tool} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-3 py-2 font-medium">{row.label}</td>
                  <td className="px-3 py-2 text-slate-600 dark:text-slate-400">{row.gen}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmt(row.f1)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmt(row.precision)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmt(row.recall)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmt(row.teds)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmt(row.gt)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmt(row.gc)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.timeMs ?? '—'}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {row.cost != null && row.cost > 0 ? row.cost.toFixed(4) : row.cost === 0 ? '0' : '—'}
                  </td>
                  <td className="px-3 py-2">{status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
