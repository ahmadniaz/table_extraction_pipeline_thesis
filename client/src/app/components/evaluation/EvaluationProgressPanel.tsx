'use client';

import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import JobStatusRow, { type ToolStatus } from './JobStatusRow';
import { type ToolId, ALL_TOOLS } from './ToolSelector';

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  .replace(/^http/, 'ws');

interface Props {
  jobId: string;
  selectedTools: ToolId[];
  totalDocs: number;
  onComplete: () => void;
}

export default function EvaluationProgressPanel({ jobId, selectedTools, totalDocs, onComplete }: Props) {
  const [toolStatuses, setToolStatuses] = useState<Record<ToolId, ToolStatus>>(
    () => Object.fromEntries(selectedTools.map(t => [t, 'waiting'])) as Record<ToolId, ToolStatus>
  );
  const [docsComplete, setDocsComplete] = useState(0);
  const [currentDoc, setCurrentDoc] = useState<string>('');
  const [finished, setFinished] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/api/ws/evaluation/${jobId}`);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'tool_start')    setToolStatuses(p => ({ ...p, [msg.tool]: 'running' }));
        if (msg.type === 'tool_done')     setToolStatuses(p => ({ ...p, [msg.tool]: 'done' }));
        if (msg.type === 'tool_failed')   setToolStatuses(p => ({ ...p, [msg.tool]: 'failed' }));
        if (msg.type === 'doc_start')     setCurrentDoc(msg.filename ?? '');
        if (msg.type === 'doc_complete')  setDocsComplete(c => c + 1);
        if (msg.type === 'job_complete') {
          setFinished(true);
          onComplete();
        }
      } catch {}
    };

    return () => ws.close();
  }, [jobId, onComplete]);

  const pct = totalDocs > 0 ? Math.round((docsComplete / totalDocs) * 100) : 0;
  const toolLabels = Object.fromEntries(ALL_TOOLS.map(t => [t.id, t.label]));

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
          {finished ? 'Evaluation complete' : 'Evaluation running…'}
        </h3>
        {finished && (
          <Link href="/results" className="flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 font-medium">
            View Results <ArrowRight className="w-4 h-4" />
          </Link>
        )}
      </div>

      {/* Overall progress */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-slate-500">
          <span>{docsComplete} / {totalDocs} documents</span>
          <span>{pct}%</span>
        </div>
        <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        {currentDoc && !finished && (
          <p className="text-xs text-slate-400 truncate">Processing: {currentDoc}</p>
        )}
      </div>

      {/* Per-tool status */}
      <div className="space-y-1.5">
        {selectedTools.map(toolId => (
          <JobStatusRow
            key={toolId}
            toolName={toolLabels[toolId] ?? toolId}
            status={toolStatuses[toolId] ?? 'waiting'}
          />
        ))}
      </div>

      {finished && (
        <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 font-medium">
          <CheckCircle2 className="w-4 h-4" />
          All tools finished. Results are ready.
        </div>
      )}
    </div>
  );
}
