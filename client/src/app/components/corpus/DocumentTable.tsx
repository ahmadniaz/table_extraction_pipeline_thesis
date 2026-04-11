'use client';

import { useState } from 'react';
import { Trash2, Eye, Edit3, FileText, Loader2, RefreshCw } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import TierBadge from './TierBadge';
import GroundTruthModal from './GroundTruthModal';
const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface Document {
  id: string;
  filename: string;
  page_count: number | null;
  is_digital: boolean | null;
  complexity_tier: 'low' | 'medium' | 'high';
  uploaded_at: string;
}

export type GtMeta =
  | { status: 'none' }
  | { status: 'confirmed'; n: number }
  | { status: 'unconfirmed'; n: number };

export type RowSeedState = 'seeding' | 'claude_unavailable' | 'no_tables' | 'seed_failed';

interface Props {
  documents: Document[];
  gtMeta: Record<string, GtMeta>;
  rowSeed: Record<string, RowSeedState>;
  onRefresh: () => void;
  onRetrySeed: (doc: Document) => void | Promise<void>;
  onOpenEditor: (doc: Document) => void;
}

export default function DocumentTable({
  documents,
  gtMeta,
  rowSeed,
  onRefresh,
  onRetrySeed,
  onOpenEditor,
}: Props) {
  const [viewGT, setViewGT] = useState<Document | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Document | null>(null);
  const [updatingTier, setUpdatingTier] = useState<string | null>(null);

  const handleTierChange = async (doc: Document, tier: string) => {
    setUpdatingTier(doc.id);
    try {
      await axios.patch(`${API}/api/documents/${doc.id}/tier`, { complexity_tier: tier });
      onRefresh();
    } catch {
      toast.error('Failed to update tier');
    } finally {
      setUpdatingTier(null);
    }
  };

  const handleDelete = async (doc: Document) => {
    setDeleting(doc.id);
    setConfirmDelete(null);
    try {
      await axios.delete(`${API}/api/documents/${doc.id}`);
      toast.success(`Deleted "${doc.filename}"`);
      onRefresh();
    } catch {
      toast.error('Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  const renderGtBadge = (doc: Document) => {
    const seed = rowSeed[doc.id];
    const meta = gtMeta[doc.id] ?? { status: 'none' as const };

    if (seed === 'seeding') {
      return (
        <div className="flex flex-col items-center gap-1">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            <Loader2 className="w-3 h-3 animate-spin shrink-0" />
            Seeding…
          </span>
          <span className="text-[10px] text-slate-500 dark:text-slate-400 text-center max-w-[200px] leading-tight">
            Extracting with Claude… (this may take 30–60 seconds)
          </span>
        </div>
      );
    }

    if (seed === 'claude_unavailable') {
      return (
        <div className="flex flex-col items-center gap-1 max-w-[220px]">
          <span className="text-[10px] text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1 leading-snug text-left">
            Claude is temporarily unavailable. You can manually add ground truth using the edit button when ready.
          </span>
        </div>
      );
    }

    if (seed === 'no_tables') {
      return (
        <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
          No tables found by Claude
        </span>
      );
    }

    if (seed === 'seed_failed') {
      return (
        <div className="flex flex-col items-center gap-1">
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200">
            Seed Failed
          </span>
          <button
            type="button"
            onClick={() => onRetrySeed(doc)}
            className="text-[10px] flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      );
    }

    if (meta.status === 'none') {
      return <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">None</span>;
    }

    if (meta.status === 'confirmed') {
      return (
        <span className="text-xs font-medium px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200">
          Confirmed ({meta.n} tables)
        </span>
      );
    }

    return (
      <span className="text-xs font-medium px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
        Unconfirmed ({meta.n} tables)
      </span>
    );
  };

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <FileText className="w-12 h-12 mb-3 opacity-40" />
        <p className="text-sm">No documents yet. Upload a PDF above.</p>
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm border-collapse">
          <thead className="bg-slate-50 dark:bg-slate-800 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Filename</th>
              <th className="px-4 py-3 text-center font-medium">Pages</th>
              <th className="px-4 py-3 text-center font-medium">Type</th>
              <th className="px-4 py-3 text-center font-medium">Tier</th>
              <th className="px-4 py-3 text-center font-medium">Ground Truth</th>
              <th className="px-4 py-3 text-center font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc, i) => (
              <tr
                key={doc.id}
                className={`border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${i === 0 ? 'border-t-0' : ''}`}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                    <span
                      className="font-medium text-slate-800 dark:text-slate-200 truncate max-w-xs"
                      title={doc.filename}
                    >
                      {doc.filename}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 pl-6">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </div>
                </td>

                <td className="px-4 py-3 text-center text-slate-600 dark:text-slate-400">
                  {doc.page_count ?? '—'}
                </td>

                <td className="px-4 py-3 text-center">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded ${
                      doc.is_digital === true
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                        : doc.is_digital === false
                          ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                          : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {doc.is_digital === true ? 'Digital' : doc.is_digital === false ? 'Scanned' : '—'}
                  </span>
                </td>

                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <TierBadge tier={doc.complexity_tier} />
                    {updatingTier === doc.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-500" />
                    ) : (
                      <select
                        value={doc.complexity_tier}
                        onChange={e => handleTierChange(doc, e.target.value)}
                        className="text-xs border border-slate-200 dark:border-slate-700 rounded px-1 py-0.5 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    )}
                  </div>
                </td>

                <td className="px-4 py-3 text-center align-middle">{renderGtBadge(doc)}</td>

                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    <button
                      type="button"
                      onClick={() => setViewGT(doc)}
                      title="View ground truth"
                      className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-indigo-600 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onOpenEditor(doc)}
                      title="Edit ground truth"
                      className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-indigo-600 transition-colors"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(doc)}
                      disabled={deleting === doc.id}
                      title="Delete document"
                      className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-400 hover:text-red-600 transition-colors disabled:opacity-40"
                    >
                      {deleting === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {viewGT && (
        <GroundTruthModal docId={viewGT.id} filename={viewGT.filename} onClose={() => setViewGT(null)} />
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">Delete document?</h3>
            <p className="text-sm text-slate-500">
              This will permanently delete <strong>{confirmDelete.filename}</strong> and all associated ground truth and
              evaluation results.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleDelete(confirmDelete)}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
