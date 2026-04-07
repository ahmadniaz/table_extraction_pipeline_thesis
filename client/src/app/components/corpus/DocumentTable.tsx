'use client';

import { useState } from 'react';
import { Trash2, Eye, Edit3, FileText, Loader2 } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import TierBadge from './TierBadge';
import GroundTruthModal from './GroundTruthModal';
import GroundTruthEditor from './GroundTruthEditor';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface Document {
  id: string;
  filename: string;
  page_count: number | null;
  is_digital: boolean | null;
  complexity_tier: 'low' | 'medium' | 'high';
  uploaded_at: string;
  ground_truth_count?: number;
}

interface Props {
  documents: Document[];
  groundTruthCounts: Record<string, number>;
  onRefresh: () => void;
}

export default function DocumentTable({ documents, groundTruthCounts, onRefresh }: Props) {
  const [viewGT, setViewGT] = useState<Document | null>(null);
  const [editGT, setEditGT] = useState<Document | null>(null);
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
                {/* Filename */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                    <span className="font-medium text-slate-800 dark:text-slate-200 truncate max-w-xs" title={doc.filename}>
                      {doc.filename}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 pl-6">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </div>
                </td>

                {/* Pages */}
                <td className="px-4 py-3 text-center text-slate-600 dark:text-slate-400">
                  {doc.page_count ?? '—'}
                </td>

                {/* Type */}
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                    doc.is_digital === true
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                      : doc.is_digital === false
                      ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {doc.is_digital === true ? 'Digital' : doc.is_digital === false ? 'Scanned' : '—'}
                  </span>
                </td>

                {/* Tier */}
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

                {/* Ground Truth */}
                <td className="px-4 py-3 text-center">
                  {groundTruthCounts[doc.id] != null ? (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                      groundTruthCounts[doc.id] > 0
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                        : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                    }`}>
                      {groundTruthCounts[doc.id] > 0 ? `${groundTruthCounts[doc.id]} table${groundTruthCounts[doc.id] !== 1 ? 's' : ''}` : 'None'}
                    </span>
                  ) : (
                    <span className="text-slate-300 text-xs">—</span>
                  )}
                </td>

                {/* Actions */}
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    <button
                      onClick={() => setViewGT(doc)}
                      title="View ground truth"
                      className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-indigo-600 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setEditGT(doc)}
                      title="Edit ground truth"
                      className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-indigo-600 transition-colors"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
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

      {/* View Ground Truth */}
      {viewGT && (
        <GroundTruthModal docId={viewGT.id} filename={viewGT.filename} onClose={() => setViewGT(null)} />
      )}

      {/* Edit Ground Truth */}
      {editGT && (
        <GroundTruthEditor
          docId={editGT.id}
          filename={editGT.filename}
          onClose={() => setEditGT(null)}
          onSaved={onRefresh}
        />
      )}

      {/* Confirm delete modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">Delete document?</h3>
            <p className="text-sm text-slate-500">
              This will permanently delete <strong>{confirmDelete.filename}</strong> and all associated ground truth and evaluation results.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
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
