'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { X, Loader2 } from 'lucide-react';
import ExtractionTableEditor, {
  type EditableExtractionTable,
  emptyExtractionTable,
  reindexExtractionTables,
} from '@/app/components/evaluation/ExtractionTableEditor';
import { sharedGetExtractionsForTool } from '@/lib/sharedExtractionsGet';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type ApiExtractionRow = {
  table_index: number;
  extracted_headers: string[] | null;
  extracted_rows: string[][] | null;
};

export type ExtractionEditorModalProps = {
  docId: string;
  toolName: string;
  toolLabel: string;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
};

function newKey(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function tablesFromApiResponse(data: ApiExtractionRow[]): EditableExtractionTable[] {
  if (!data.length) {
    return [emptyExtractionTable(0)];
  }
  const sorted = [...data].sort((a, b) => a.table_index - b.table_index);
  return reindexExtractionTables(
    sorted.map(er => ({
      localKey: newKey(),
      table_index: er.table_index,
      headers: (er.extracted_headers || []).map(h => String(h ?? '')),
      rows: (er.extracted_rows || []).map(r =>
        (Array.isArray(r) ? r : []).map(c => String(c ?? ''))
      ),
    }))
  );
}

function cloneTables(t: EditableExtractionTable[]): EditableExtractionTable[] {
  return t.map(x => ({
    ...x,
    headers: [...x.headers],
    rows: x.rows.map(r => [...r]),
  }));
}

export default function ExtractionEditorModal({
  docId,
  toolName,
  toolLabel,
  isOpen,
  onClose,
  onSaved,
}: ExtractionEditorModalProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draftTables, setDraftTables] = useState<EditableExtractionTable[]>([emptyExtractionTable(0)]);
  const [initialSnapshot, setInitialSnapshot] = useState<EditableExtractionTable[]>([emptyExtractionTable(0)]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await sharedGetExtractionsForTool<ApiExtractionRow[]>(docId, toolName);
      const mapped = tablesFromApiResponse(data || []);
      setDraftTables(mapped);
      setInitialSnapshot(cloneTables(mapped));
    } catch {
      toast.error('Failed to load extraction');
      const fallback = [emptyExtractionTable(0)];
      setDraftTables(fallback);
      setInitialSnapshot(cloneTables(fallback));
    } finally {
      setLoading(false);
    }
  }, [docId, toolName]);

  useEffect(() => {
    if (!isOpen || !toolName) return;
    void load();
  }, [isOpen, toolName, load]);

  const handleCancel = () => {
    setDraftTables(cloneTables(initialSnapshot));
    onClose();
  };

  const handleSave = async () => {
    if (!draftTables.length) {
      toast.error('Add at least one table');
      return;
    }
    setSaving(true);
    try {
      await axios.put(`${API}/api/extractions/${docId}/${toolName}`, {
        tables: draftTables.map(t => ({
          headers: t.headers,
          rows: t.rows,
        })),
      });
      toast.success('Extraction saved');
      await load();
      onSaved();
      onClose();
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { detail?: string } } };
      toast.error(ax?.response?.data?.detail ?? 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-2 sm:p-4 bg-black/50">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-[min(98vw,1200px)] h-[min(92vh,880px)] flex flex-col">
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Edit extraction</h2>
            <p className="text-sm text-slate-500 truncate max-w-md">
              {toolLabel} · table order becomes table_index 0…n−1 for evaluation
            </p>
          </div>
          <button type="button" onClick={handleCancel} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          </div>
        ) : (
          <>
            <ExtractionTableEditor tables={draftTables} onChange={setDraftTables} enableMerge enableReorder />
            <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2 shrink-0 bg-white dark:bg-slate-900">
              <button
                type="button"
                onClick={handleCancel}
                disabled={saving}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !draftTables.length}
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Save extraction
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
