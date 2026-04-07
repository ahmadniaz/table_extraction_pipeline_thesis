'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { BookOpen, RefreshCw } from 'lucide-react';
import DocumentUploadZone from '@/app/components/corpus/DocumentUploadZone';
import DocumentTable, { type Document } from '@/app/components/corpus/DocumentTable';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function CorpusPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [gtCounts, setGtCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get<Document[]>(`${API}/api/documents/`);
      setDocuments(data);

      // Fetch ground truth counts in parallel
      const counts = await Promise.all(
        data.map(async (doc) => {
          try {
            const r = await axios.get<any[]>(`${API}/api/ground-truth/${doc.id}`);
            return [doc.id, r.data.length] as const;
          } catch {
            return [doc.id, 0] as const;
          }
        })
      );
      setGtCounts(Object.fromEntries(counts));
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg">
          <BookOpen className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Document Corpus</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Upload PDFs and annotate ground truth tables for evaluation</p>
        </div>
      </div>

      {/* Upload zone */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-4">Upload Document</h2>
        <DocumentUploadZone onUploaded={fetchDocuments} />
      </div>

      {/* Document list */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Documents</h2>
            {!loading && (
              <p className="text-xs text-slate-400 mt-0.5">{documents.length} document{documents.length !== 1 ? 's' : ''}</p>
            )}
          </div>
          <button
            onClick={fetchDocuments}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-indigo-500" />
            </div>
          ) : (
            <DocumentTable
              documents={documents}
              groundTruthCounts={gtCounts}
              onRefresh={fetchDocuments}
            />
          )}
        </div>
      </div>
    </div>
  );
}
