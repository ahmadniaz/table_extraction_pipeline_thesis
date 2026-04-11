'use client';

import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import axios from 'axios';
import { cn } from '@/lib/utils';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface ExtChunk {
  table_index: number;
  extracted_headers: string[] | null;
  extracted_rows: string[][] | null;
}

interface GTChunk {
  table_index: number;
  headers: string[];
  rows: string[][];
}

interface Props {
  docId: string;
  filename: string;
  toolName: string;
  toolLabel: string;
  onClose: () => void;
}

function ReadonlyTable({ title, headers, rows }: { title: string; headers: string[]; rows: string[][] }) {
  return (
    <div className="flex flex-col min-h-0 h-full">
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2 shrink-0">{title}</h3>
      <div className="flex-1 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="text-xs w-full border-collapse min-w-max">
          <thead className="sticky top-0 bg-slate-100 dark:bg-slate-800 z-10">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="text-left px-2 py-2 border-b border-slate-200 dark:border-slate-600 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-white dark:bg-slate-900' : 'bg-slate-50 dark:bg-slate-800/80'}>
                {row.map((cell, ci) => (
                  <td key={ci} className="px-2 py-1.5 border-b border-slate-100 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ExtractionPreviewModal({ docId, filename, toolName, toolLabel, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [ext, setExt] = useState<ExtChunk[]>([]);
  const [gt, setGt] = useState<GTChunk[]>([]);
  const [tabExt, setTabExt] = useState(0);
  const [tabGt, setTabGt] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [exRes, gtRes] = await Promise.all([
          axios.get<
            {
              table_index: number;
              extracted_headers: string[] | null;
              extracted_rows: string[][] | null;
            }[]
          >(`${API}/api/extractions/${docId}/${toolName}`),
          axios.get<{ table_index: number; headers: string[]; rows: string[][]; confirmed?: boolean }[]>(
            `${API}/api/ground-truth/${docId}`
          ),
        ]);
        if (cancelled) return;
        const chunks: ExtChunk[] = (exRes.data || []).map(e => ({
          table_index: e.table_index,
          extracted_headers: e.extracted_headers,
          extracted_rows: e.extracted_rows,
        }));
        setExt(chunks);
        const confirmed = (gtRes.data || []).filter(t => t.confirmed === true);
        setGt(
          confirmed.map(t => ({
            table_index: t.table_index,
            headers: t.headers || [],
            rows: t.rows || [],
          }))
        );
      } catch (e: unknown) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Load failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId, toolName]);

  const tablesCount = ext.filter(e => e.extracted_rows && e.extracted_rows.length > 0).length;

  const extCur = ext[tabExt];
  const extHeaders = extCur?.extracted_headers ?? [];
  const extRows = extCur?.extracted_rows ?? [];

  const gtCur = gt[tabGt];
  const gtHeaders = gtCur?.headers ?? [];
  const gtRows = gtCur?.rows ?? [];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-2 sm:p-6 bg-black/60">
      <div
        className={cn(
          'bg-white dark:bg-slate-900 rounded-xl shadow-2xl flex flex-col overflow-hidden',
          'w-full max-w-[80vw] max-h-[90vh] min-h-[320px]'
        )}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {filename} · {toolLabel} · {tablesCount} table{tablesCount !== 1 ? 's' : ''} extracted
            </p>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Preview</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center py-24">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          </div>
        ) : err ? (
          <p className="p-8 text-center text-red-600">{err}</p>
        ) : (
          <div className="flex-1 flex flex-col md:flex-row min-h-0 gap-0">
            <div className="flex-1 min-h-[200px] md:min-h-0 p-4 border-b md:border-b-0 md:border-r border-slate-200 dark:border-slate-700 flex flex-col">
              {ext.length > 1 && (
                <div className="flex gap-1 mb-2 flex-wrap shrink-0">
                  {ext.map((e, i) => (
                    <button
                      key={e.table_index}
                      type="button"
                      onClick={() => setTabExt(i)}
                      className={cn(
                        'px-2 py-1 text-xs rounded',
                        i === tabExt ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600'
                      )}
                    >
                      Table {e.table_index}
                    </button>
                  ))}
                </div>
              )}
              <ReadonlyTable title={`${toolLabel} Output`} headers={extHeaders} rows={extRows} />
            </div>
            <div className="flex-1 min-h-[200px] md:min-h-0 p-4 flex flex-col">
              {gt.length > 1 && (
                <div className="flex gap-1 mb-2 flex-wrap shrink-0">
                  {gt.map((g, i) => (
                    <button
                      key={g.table_index}
                      type="button"
                      onClick={() => setTabGt(i)}
                      className={cn(
                        'px-2 py-1 text-xs rounded',
                        i === tabGt ? 'bg-emerald-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600'
                      )}
                    >
                      Table {g.table_index}
                    </button>
                  ))}
                </div>
              )}
              <ReadonlyTable title="Ground Truth" headers={gtHeaders} rows={gtRows} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
