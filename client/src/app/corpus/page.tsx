'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { BookOpen, RefreshCw } from 'lucide-react';
import DocumentUploadZone, { type UploadedDocumentPayload } from '@/app/components/corpus/DocumentUploadZone';
import DocumentTable, {
  type Document,
  type GtMeta,
  type RowSeedState,
} from '@/app/components/corpus/DocumentTable';
import GroundTruthEditor from '@/app/components/corpus/GroundTruthEditor';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function fetchGtMetaForDocs(docs: Document[]): Promise<Record<string, GtMeta>> {
  const entries = await Promise.all(
    docs.map(async d => {
      try {
        const { data } = await axios.get<
          { confirmed?: boolean; table_index: number }[]
        >(`${API}/api/ground-truth/${d.id}`);
        if (!data.length) return [d.id, { status: 'none' as const }] as const;
        const allConfirmed = data.every(r => r.confirmed === true);
        if (allConfirmed) return [d.id, { status: 'confirmed' as const, n: data.length }] as const;
        return [d.id, { status: 'unconfirmed' as const, n: data.length }] as const;
      } catch {
        return [d.id, { status: 'none' as const }] as const;
      }
    })
  );
  return Object.fromEntries(entries);
}

export default function CorpusPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [gtMeta, setGtMeta] = useState<Record<string, GtMeta>>({});
  const [rowSeed, setRowSeed] = useState<Record<string, RowSeedState>>({});
  const [loading, setLoading] = useState(true);
  const [editorDoc, setEditorDoc] = useState<Document | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get<Document[]>(`${API}/api/documents/`);
      setDocuments(data);
      setGtMeta(await fetchGtMetaForDocs(data));
    } catch {
      setDocuments([]);
      setGtMeta({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const runSeedForDoc = useCallback(async (doc: UploadedDocumentPayload | Document) => {
    setRowSeed(prev => ({ ...prev, [doc.id]: 'seeding' }));
    try {
      const r = await axios.post<{
        tables_seeded?: number;
        message?: string;
      }>(`${API}/api/documents/${doc.id}/seed-ground-truth`);
      const n = r.data.tables_seeded ?? 0;
      if (n === 0) {
        setRowSeed(prev => ({ ...prev, [doc.id]: 'no_tables' }));
      } else {
        setRowSeed(prev => {
          const next = { ...prev };
          delete next[doc.id];
          return next;
        });
        const tier = ('complexity_tier' in doc ? doc.complexity_tier : 'medium') as Document['complexity_tier'];
        setEditorDoc({
          id: doc.id,
          filename: doc.filename,
          complexity_tier: tier,
          page_count: 'page_count' in doc ? doc.page_count : null,
          is_digital: 'is_digital' in doc ? doc.is_digital : null,
          uploaded_at: 'uploaded_at' in doc ? doc.uploaded_at : new Date().toISOString(),
        });
      }
      await fetchDocuments();
    } catch (e: unknown) {
      const ax = e as { response?: { status?: number } };
      if (ax.response?.status === 503) {
        setRowSeed(prev => ({ ...prev, [doc.id]: 'claude_unavailable' }));
      } else {
        setRowSeed(prev => ({ ...prev, [doc.id]: 'seed_failed' }));
      }
      await fetchDocuments();
    }
  }, [fetchDocuments]);

  const handleUploaded = useCallback(
    async (doc: UploadedDocumentPayload) => {
      await fetchDocuments();
      await runSeedForDoc(doc);
    },
    [fetchDocuments, runSeedForDoc]
  );

  const handleRetrySeed = useCallback(
    async (doc: Document) => {
      await runSeedForDoc(doc);
    },
    [runSeedForDoc]
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg">
          <BookOpen className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Document Corpus</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Upload PDFs, review automated seed extraction, confirm ground truth, then evaluate
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-4">
          Upload Document
        </h2>
        <DocumentUploadZone onUploaded={handleUploaded} />
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Documents</h2>
            {!loading && (
              <p className="text-xs text-slate-400 mt-0.5">
                {documents.length} document{documents.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>
          <button
            type="button"
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
              gtMeta={gtMeta}
              rowSeed={rowSeed}
              onRefresh={fetchDocuments}
              onRetrySeed={handleRetrySeed}
              onOpenEditor={setEditorDoc}
            />
          )}
        </div>
      </div>

      {editorDoc && (
        <GroundTruthEditor
          docId={editorDoc.id}
          filename={editorDoc.filename}
          onClose={() => setEditorDoc(null)}
          onSaved={() => {
            const id = editorDoc.id;
            setRowSeed(prev => {
              const next = { ...prev };
              delete next[id];
              return next;
            });
            fetchDocuments();
          }}
        />
      )}
    </div>
  );
}
