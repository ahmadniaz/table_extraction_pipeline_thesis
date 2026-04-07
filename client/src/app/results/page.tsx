'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart2, Download, RefreshCw, Loader2 } from 'lucide-react';
import MetricsSummaryTable, { type ToolSummary } from '@/app/components/results/MetricsSummaryTable';
import ComplexityBarChart from '@/app/components/results/ComplexityBarChart';
import TedsTrendChart from '@/app/components/results/TedsTrendChart';
import DocumentDrillDown from '@/app/components/results/DocumentDrillDown';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

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
}

interface Document { id: string; filename: string; }

function avg(vals: (number | null)[]): number | null {
  const nums = vals.filter((v): v is number => v != null);
  return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}

function buildToolSummaries(rows: RawRow[]): ToolSummary[] {
  const byTool: Record<string, RawRow[]> = {};
  for (const r of rows) {
    (byTool[r.tool_name] ??= []).push(r);
  }
  return Object.entries(byTool).map(([tool, rs]) => ({
    tool_name: tool,
    avg_precision: avg(rs.map(r => r.precision)),
    avg_recall:    avg(rs.map(r => r.recall)),
    avg_f1:        avg(rs.map(r => r.f1_score)),
    avg_teds:      avg(rs.map(r => r.teds_score)),
    avg_grits_top: avg(rs.map(r => r.grits_top)),
    avg_grits_con: avg(rs.map(r => r.grits_con)),
    cost_per_page: avg(rs.map(r => r.cost_usd)),
    avg_time_ms:   avg(rs.map(r => r.processing_time_ms)),
  }));
}

function buildChartData(rows: RawRow[], metric: 'f1_score' | 'teds_score') {
  const tiers = ['low', 'medium', 'high'];
  const tools = [...new Set(rows.map(r => r.tool_name))];

  return tiers.map(tier => {
    const tierRows = rows.filter(r => r.complexity_tier === tier);
    const entry: Record<string, number | string> = { tier };
    for (const tool of tools) {
      const toolRows = tierRows.filter(r => r.tool_name === tool);
      const a = avg(toolRows.map(r => r[metric]));
      if (a != null) entry[tool] = parseFloat(a.toFixed(4));
    }
    return entry;
  });
}

function buildResultsByDoc(rows: RawRow[]) {
  const out: Record<string, any[]> = {};
  for (const r of rows) {
    (out[r.document_id] ??= []).push(r);
  }
  return out;
}

export default function ResultsPage() {
  const [rows, setRows] = useState<RawRow[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [resResults, resDocs] = await Promise.all([
        axios.get<RawRow[]>(`${API}/api/results/`),
        axios.get<Document[]>(`${API}/api/documents/`),
      ]);
      setRows(resResults.data);
      setDocuments(resDocs.data);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const summaries = buildToolSummaries(rows);
  const tools = [...new Set(rows.map(r => r.tool_name))];
  const f1ChartData = buildChartData(rows, 'f1_score');
  const tedsChartData = buildChartData(rows, 'teds_score');
  const resultsByDoc = buildResultsByDoc(rows);

  const handleExport = () => {
    window.open(`${API}/api/results/export/csv`, '_blank');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
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
            onClick={fetchData}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleExport}
            disabled={rows.length === 0}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        </div>
      ) : (
        <>
          {/* Summary metrics table */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Summary by Tool</h2>
            </div>
            <div className="p-6">
              <MetricsSummaryTable data={summaries} />
            </div>
          </div>

          {/* Charts */}
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

          {/* Per-document drill-down */}
          {documents.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Per-Document Drill-Down</h2>
              </div>
              <div className="p-6">
                <DocumentDrillDown documents={documents} resultsByDoc={resultsByDoc} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
