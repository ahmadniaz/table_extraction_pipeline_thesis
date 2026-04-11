'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import axios from 'axios';
import { BarChart2, Download, RefreshCw, Loader2 } from 'lucide-react';
import MetricsSummaryTable, { type ToolSummary } from '@/app/components/results/MetricsSummaryTable';
import ComplexityBarChart from '@/app/components/results/ComplexityBarChart';
import TedsTrendChart from '@/app/components/results/TedsTrendChart';
import DocumentDrillDown from '@/app/components/results/DocumentDrillDown';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const TOOL_LABELS: Record<string, string> = {
  pymupdf: 'PyMuPDF',
  docling: 'Docling',
  google_docai: 'Google DocAI',
  gpt5: 'GPT-5 Vision',
  claude_sonnet: 'Claude Sonnet',
  mistral: 'Mistral AI',
};

interface RawRow {
  document_id: string;
  filename: string;
  complexity_tier: string;
  tool_name: string;
  table_index: number;
  processing_time_ms: number | null;
  cost_usd: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  teds_score: number | null;
  grits_top: number | null;
  grits_con: number | null;
  grits_loc: number | null;
  error?: string | null;
  failure_reason?: string | null;
  is_transient_failure?: boolean;
}

interface DocumentRow {
  id: string;
  filename: string;
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
}

function avg(vals: (number | null)[]): number | null {
  const nums = vals.filter((v): v is number => v != null);
  return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}

function rowsExcludingTransient(rows: RawRow[]): RawRow[] {
  return rows.filter(r => !r.is_transient_failure);
}

function buildToolSummaries(rows: RawRow[]): ToolSummary[] {
  const filtered = rowsExcludingTransient(rows);
  const byTool: Record<string, RawRow[]> = {};
  for (const r of filtered) {
    (byTool[r.tool_name] ??= []).push(r);
  }
  return Object.entries(byTool).map(([tool, rs]) => ({
    tool_name: tool,
    avg_precision: avg(rs.map(r => r.precision)),
    avg_recall: avg(rs.map(r => r.recall)),
    avg_f1: avg(rs.map(r => r.f1_score)),
    avg_teds: avg(rs.map(r => r.teds_score)),
    avg_grits_top: avg(rs.map(r => r.grits_top)),
    avg_grits_con: avg(rs.map(r => r.grits_con)),
    cost_per_page: avg(rs.map(r => r.cost_usd)),
    avg_time_ms: avg(rs.map(r => r.processing_time_ms)),
  }));
}

function buildChartData(rows: RawRow[], metric: 'f1_score' | 'teds_score') {
  const filtered = rowsExcludingTransient(rows);
  const tiers = ['low', 'medium', 'high'];
  const tools = [...new Set(filtered.map(r => r.tool_name))];

  return tiers.map(tier => {
    const tierRows = filtered.filter(r => r.complexity_tier === tier);
    const entry: Record<string, number | string> = { tier };
    for (const tool of tools) {
      const toolRows = tierRows.filter(r => r.tool_name === tool);
      const a = avg(toolRows.map(r => r[metric]));
      if (a != null) entry[tool] = parseFloat(a.toFixed(4));
    }
    return entry;
  });
}

/** Shape expected by DocumentDrillDown */
interface DrillResultRow {
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

function buildResultsByDoc(rows: RawRow[]): Record<string, DrillResultRow[]> {
  const out: Record<string, DrillResultRow[]> = {};
  for (const r of rows) {
    (out[r.document_id] ??= []).push({
      tool_name: r.tool_name,
      table_index: r.table_index,
      processing_time_ms: r.processing_time_ms,
      cost_usd: r.cost_usd,
      error: r.error ?? null,
      precision: r.precision,
      recall: r.recall,
      f1_score: r.f1_score,
      teds_score: r.teds_score,
      grits_top: r.grits_top,
    });
  }
  return out;
}

interface PerDocSummary {
  doc: DocumentRow;
  bestTool: string | null;
  avgF1: number | null;
  gtTables: number;
}

function buildPerDocSummaries(docs: DocumentRow[], rows: RawRow[], gtCounts: Record<string, number>): PerDocSummary[] {
  return docs.map(doc => {
    const dr = rows.filter(r => r.document_id === doc.id && !r.is_transient_failure);
    const byTool: Record<string, RawRow[]> = {};
    for (const r of dr) {
      (byTool[r.tool_name] ??= []).push(r);
    }
    const toolF1 = Object.entries(byTool).map(([name, rs]) => ({
      name,
      f1: avg(rs.map(x => x.f1_score)),
    }));
    toolF1.sort((a, b) => (b.f1 ?? -1) - (a.f1 ?? -1));
    const best = toolF1[0];
    return {
      doc,
      bestTool: best?.name ?? null,
      avgF1: avg(dr.map(x => x.f1_score)),
      gtTables: gtCounts[doc.id] ?? 0,
    };
  });
}

export default function ResultsPage() {
  const [tab, setTab] = useState<'summary' | 'perDoc'>('summary');
  const [rows, setRows] = useState<RawRow[]>([]);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [gtCounts, setGtCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [resResults, resDocs] = await Promise.all([
        axios.get<RawRow[]>(`${API}/api/results/`),
        axios.get<DocumentRow[]>(`${API}/api/documents/`),
      ]);
      setRows(resResults.data);
      setDocuments(resDocs.data);

      const gcEntries = await Promise.all(
        resDocs.data.map(async d => {
          try {
            const r = await axios.get<{ confirmed?: boolean }[]>(`${API}/api/ground-truth/${d.id}`);
            return [d.id, r.data.length] as const;
          } catch {
            return [d.id, 0] as const;
          }
        })
      );
      setGtCounts(Object.fromEntries(gcEntries));
    } catch {
      setRows([]);
      setDocuments([]);
      setGtCounts({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const summaries = buildToolSummaries(rows);
  const filteredRows = rowsExcludingTransient(rows);
  const tools = [...new Set(filteredRows.map(r => r.tool_name))];
  const f1ChartData = buildChartData(rows, 'f1_score');
  const tedsChartData = buildChartData(rows, 'teds_score');
  const resultsByDoc = buildResultsByDoc(rows);
  const perDocSummaries = buildPerDocSummaries(documents, rows, gtCounts);

  const handleExport = () => {
    window.open(`${API}/api/results/export/csv`, '_blank');
  };

  const handleExportPerDoc = () => {
    window.open(`${API}/api/results/export/per-document-csv`, '_blank');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg">
            <BarChart2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Evaluation Results</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {rows.length > 0
                ? `${rows.length} scored results across ${documents.length} documents`
                : 'No results yet — run an evaluation first'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {tab === 'summary' && (
            <button
              type="button"
              onClick={handleExport}
              disabled={rows.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          )}
        </div>
      </div>

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        <button
          type="button"
          onClick={() => setTab('summary')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === 'summary'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          Summary
        </button>
        <button
          type="button"
          onClick={() => setTab('perDoc')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === 'perDoc'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          Per Document
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        </div>
      ) : tab === 'summary' ? (
        <>
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
                Summary by Tool
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Averages exclude rows where <code className="text-[10px]">is_transient_failure</code> is true.
              </p>
            </div>
            <div className="p-6">
              <MetricsSummaryTable data={summaries} />
            </div>
          </div>

          {rows.length > 0 && tools.length > 0 && (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-4">
                  F1 Score by Tool &amp; Complexity Tier
                </h2>
                <ComplexityBarChart data={f1ChartData} tools={tools} />
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-4">
                  TEDS Score per Tool across Tiers
                </h2>
                <TedsTrendChart data={tedsChartData} tools={tools} />
              </div>
            </div>
          )}

          {documents.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
                  Per-Document Drill-Down
                </h2>
              </div>
              <div className="p-6">
                <DocumentDrillDown documents={documents} resultsByDoc={resultsByDoc} />
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-x-auto">
            <table className="w-full text-sm min-w-[800px]">
              <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="text-left px-4 py-3">Filename</th>
                  <th className="text-center px-4 py-3">Tier</th>
                  <th className="text-center px-4 py-3">Pages</th>
                  <th className="text-center px-4 py-3">Type</th>
                  <th className="text-left px-4 py-3">Best Tool</th>
                  <th className="text-right px-4 py-3">Avg F1</th>
                  <th className="text-center px-4 py-3">GT Tables</th>
                  <th className="text-right px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {perDocSummaries.map(({ doc, bestTool, avgF1, gtTables }) => (
                  <tr key={doc.id} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200 max-w-[200px] truncate">
                      {doc.filename}
                    </td>
                    <td className="px-4 py-3 text-center text-xs">{doc.complexity_tier}</td>
                    <td className="px-4 py-3 text-center">{doc.page_count ?? '—'}</td>
                    <td className="px-4 py-3 text-center text-xs">
                      {doc.is_digital === true ? 'Digital' : doc.is_digital === false ? 'Scanned' : '—'}
                    </td>
                    <td className="px-4 py-3">{bestTool ? TOOL_LABELS[bestTool] ?? bestTool : '—'}</td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {avgF1 != null ? avgF1.toFixed(4) : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">{gtTables}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/results/${doc.id}`}
                        className="text-indigo-600 dark:text-indigo-400 hover:underline text-xs font-medium"
                      >
                        View Results
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleExport}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Download className="w-4 h-4" />
              Export All Results
            </button>
            <button
              type="button"
              onClick={handleExportPerDoc}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
            >
              <Download className="w-4 h-4" />
              Export Per-Document Summary
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
