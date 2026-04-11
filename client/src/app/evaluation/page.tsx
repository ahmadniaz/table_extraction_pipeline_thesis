'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { Play, Loader2, Zap } from 'lucide-react';
import toast from 'react-hot-toast';
import ToolSelector, { DEFAULT_SELECTED_TOOLS, type ToolId } from '@/app/components/evaluation/ToolSelector';
import EvaluationProgressPanel from '@/app/components/evaluation/EvaluationProgressPanel';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type Tier = 'all' | 'low' | 'medium' | 'high';

interface Document { id: string; filename: string; complexity_tier: string; }

export default function EvaluationPage() {
  const [selectedTools, setSelectedTools] = useState<ToolId[]>(DEFAULT_SELECTED_TOOLS);
  const [tier, setTier] = useState<Tier>('all');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docFilter, setDocFilter] = useState<'all' | string>('all');
  const [docSearch, setDocSearch] = useState('');

  const [running, setRunning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [totalDocs, setTotalDocs] = useState(0);

  useEffect(() => {
    axios.get<Document[]>(`${API}/api/documents/`)
      .then(r => setDocuments(r.data))
      .catch(() => {});
  }, []);

  const filteredDocs = documents.filter(d => {
    const matchesTier = tier === 'all' || d.complexity_tier === tier;
    const matchesSearch = d.filename.toLowerCase().includes(docSearch.toLowerCase());
    return matchesTier && matchesSearch;
  });

  const docsToEvaluate = docFilter === 'all'
    ? filteredDocs
    : filteredDocs.filter(d => d.id === docFilter);

  const handleRun = useCallback(async () => {
    if (selectedTools.length === 0) { toast.error('Select at least one tool'); return; }
    if (docsToEvaluate.length === 0) { toast.error('No documents match the filter'); return; }

    setRunning(true);
    const id = crypto.randomUUID();
    setJobId(id);
    setTotalDocs(docsToEvaluate.length);

    try {
      await axios.post(`${API}/api/evaluate/batch`, {
        tools: selectedTools,
        tier,
      });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Evaluation failed to start');
      setRunning(false);
      setJobId(null);
    }
  }, [selectedTools, docsToEvaluate, tier]);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg">
          <Zap className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Run Evaluation</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Select tools and documents, then run the benchmark</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration */}
        <div className="space-y-6">
          {/* Tool selector */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
            <ToolSelector selected={selectedTools} onChange={setSelectedTools} />
          </div>

          {/* Tier filter */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Complexity Tier</h3>
            <div className="flex flex-wrap gap-2">
              {(['all', 'low', 'medium', 'high'] as Tier[]).map(t => (
                <label key={t} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value={t}
                    checked={tier === t}
                    onChange={() => setTier(t)}
                    className="accent-indigo-600"
                  />
                  <span className="text-sm text-slate-700 dark:text-slate-300 capitalize">{t}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Document selector */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Documents</h3>
            <input
              type="text"
              value={docSearch}
              onChange={e => setDocSearch(e.target.value)}
              placeholder="Search by filename…"
              className="w-full text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <div className="max-h-40 overflow-y-auto space-y-1">
              <label className="flex items-center gap-2 cursor-pointer py-1">
                <input type="radio" value="all" checked={docFilter === 'all'} onChange={() => setDocFilter('all')} className="accent-indigo-600" />
                <span className="text-sm text-slate-700 dark:text-slate-300">All matching documents ({filteredDocs.length})</span>
              </label>
              {filteredDocs.map(d => (
                <label key={d.id} className="flex items-center gap-2 cursor-pointer py-1">
                  <input type="radio" value={d.id} checked={docFilter === d.id} onChange={() => setDocFilter(d.id)} className="accent-indigo-600" />
                  <span className="text-sm text-slate-600 dark:text-slate-400 truncate">{d.filename}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Run button */}
          <button
            onClick={handleRun}
            disabled={running || selectedTools.length === 0 || docsToEvaluate.length === 0}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running
              ? 'Running…'
              : `Run Evaluation on ${docsToEvaluate.length} document${docsToEvaluate.length !== 1 ? 's' : ''}`
            }
          </button>
        </div>

        {/* Progress panel */}
        <div>
          {jobId ? (
            <EvaluationProgressPanel
              jobId={jobId}
              selectedTools={selectedTools}
              totalDocs={totalDocs}
              onComplete={() => setRunning(false)}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-300 dark:text-slate-600 py-20">
              <Play className="w-12 h-12 mb-3 opacity-40" />
              <p className="text-sm">Configure and click Run to start</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
