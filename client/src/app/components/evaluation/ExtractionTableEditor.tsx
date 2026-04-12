'use client';

import { useCallback, useMemo, useState } from 'react';
import { Plus, Trash2, X, ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export type EditableExtractionTable = {
  localKey: string;
  table_index: number;
  headers: string[];
  rows: string[][];
};

function newLocalKey(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function emptyExtractionTable(index: number): EditableExtractionTable {
  return {
    localKey: newLocalKey(),
    table_index: index,
    headers: ['Col 1', 'Col 2'],
    rows: [['', '']],
  };
}

export function reindexExtractionTables(tables: EditableExtractionTable[]): EditableExtractionTable[] {
  return tables.map((t, i) => ({ ...t, table_index: i }));
}

function padRow(row: string[], width: number): string[] {
  const cells = row.map(c => String(c ?? ''));
  while (cells.length < width) cells.push('');
  return cells.slice(0, width);
}

function mergeTwoTables(
  primary: EditableExtractionTable,
  secondary: EditableExtractionTable
): EditableExtractionTable {
  const w = primary.headers.length;
  const mergedRows = [
    ...primary.rows.map(r => padRow(r, w)),
    ...secondary.rows.map(r => padRow(r, w)),
  ];
  return {
    ...primary,
    rows: mergedRows,
  };
}

type Props = {
  tables: EditableExtractionTable[];
  onChange: (next: EditableExtractionTable[]) => void;
  enableMerge?: boolean;
  enableReorder?: boolean;
};

export default function ExtractionTableEditor({
  tables,
  onChange,
  enableMerge = true,
  enableReorder = true,
}: Props) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [mergingKey, setMergingKey] = useState<string | null>(null);
  const [mergeTargetKey, setMergeTargetKey] = useState<string | null>(null);

  const t = tables[activeIdx];

  const resetTables = useCallback(
    (next: EditableExtractionTable[], nextActive: number) => {
      onChange(reindexExtractionTables(next));
      setActiveIdx(Math.max(0, Math.min(nextActive, next.length - 1)));
    },
    [onChange]
  );

  const updateTable = useCallback(
    (patch: Partial<EditableExtractionTable>) => {
      onChange(
        reindexExtractionTables(
          tables.map((tbl, i) => (i === activeIdx ? { ...tbl, ...patch } : tbl))
        )
      );
    },
    [activeIdx, onChange, tables]
  );

  const setHeader = (ci: number, val: string) => {
    if (!t) return;
    const headers = [...t.headers];
    headers[ci] = val;
    updateTable({ headers });
  };

  const setCell = (ri: number, ci: number, val: string) => {
    if (!t) return;
    const rows = t.rows.map((r, i) => (i === ri ? r.map((c, j) => (j === ci ? val : c)) : r));
    updateTable({ rows });
  };

  const addColumn = () => {
    if (!t) return;
    updateTable({
      headers: [...t.headers, `Col ${t.headers.length + 1}`],
      rows: t.rows.map(r => [...r, '']),
    });
  };

  const removeColumn = (ci: number) => {
    if (!t) return;
    updateTable({
      headers: t.headers.filter((_, i) => i !== ci),
      rows: t.rows.map(r => r.filter((_, i) => i !== ci)),
    });
  };

  const addRow = () => {
    if (!t) return;
    updateTable({ rows: [...t.rows, Array(t.headers.length).fill('')] });
  };

  const removeRow = (ri: number) => {
    if (!t) return;
    updateTable({ rows: t.rows.filter((_, i) => i !== ri) });
  };

  const deleteTableAt = (arrayIndex: number) => {
    if (tables.length === 1) {
      resetTables([emptyExtractionTable(0)], 0);
      setMergingKey(null);
      setMergeTargetKey(null);
      return;
    }
    const next = tables.filter((_, i) => i !== arrayIndex);
    let na = activeIdx;
    if (arrayIndex < activeIdx) na = activeIdx - 1;
    else if (arrayIndex === activeIdx) na = Math.min(activeIdx, next.length - 1);
    if (mergingKey && !next.some(x => x.localKey === mergingKey)) setMergingKey(null);
    setMergeTargetKey(null);
    resetTables(next, na);
  };

  const addTable = () => {
    resetTables([...tables, emptyExtractionTable(tables.length)], tables.length);
  };

  const moveTable = (from: number, dir: -1 | 1) => {
    const to = from + dir;
    if (to < 0 || to >= tables.length) return;
    const next = [...tables];
    [next[from], next[to]] = [next[to], next[from]];
    resetTables(next, to);
  };

  const confirmMerge = useCallback(() => {
    if (!mergingKey || !mergeTargetKey || mergingKey === mergeTargetKey) return;
    const a = tables.find(x => x.localKey === mergingKey);
    const b = tables.find(x => x.localKey === mergeTargetKey);
    if (!a || !b) return;
    const primary = a.table_index <= b.table_index ? a : b;
    const secondary = a.table_index <= b.table_index ? b : a;
    const merged = mergeTwoTables(primary, secondary);
    const next2 = tables
      .filter(x => x.localKey !== secondary.localKey)
      .map(x => (x.localKey === primary.localKey ? { ...merged, localKey: primary.localKey } : x));
    const pi = next2.findIndex(x => x.localKey === primary.localKey);
    setMergingKey(null);
    setMergeTargetKey(null);
    resetTables(next2, Math.max(0, pi));
  }, [mergeTargetKey, mergingKey, resetTables, tables]);

  const mergePanel = useMemo(() => {
    if (!enableMerge || !mergingKey) return null;
    const others = tables.filter(x => x.localKey !== mergingKey);
    return (
      <div className="mx-3 mt-2 p-3 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 text-sm">
        <p className="text-slate-700 dark:text-slate-200 font-medium mb-2">Merge another table into this one:</p>
        <div className="flex flex-wrap gap-2">
          {others.length === 0 && <p className="text-xs text-slate-500">No other tables.</p>}
          {others.map(tbl => (
            <button
              key={tbl.localKey}
              type="button"
              onClick={() => setMergeTargetKey(tbl.localKey)}
              className={cn(
                'px-2 py-1.5 text-xs rounded border text-left max-w-full',
                mergeTargetKey === tbl.localKey
                  ? 'border-indigo-500 bg-indigo-100 dark:bg-indigo-900/40'
                  : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800'
              )}
            >
              Table {tbl.table_index + 1}: {tbl.headers.slice(0, 3).join(', ') || '…'}
            </button>
          ))}
        </div>
        {mergeTargetKey && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={confirmMerge}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
            >
              Confirm merge
            </button>
            <button
              type="button"
              onClick={() => setMergeTargetKey(null)}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={() => {
                setMergingKey(null);
                setMergeTargetKey(null);
              }}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600"
            >
              Cancel
            </button>
          </div>
        )}
        {!mergeTargetKey && (
          <button
            type="button"
            className="mt-2 text-xs text-slate-600 dark:text-slate-400 hover:underline"
            onClick={() => {
              setMergingKey(null);
              setMergeTargetKey(null);
            }}
          >
            Cancel merge
          </button>
        )}
      </div>
    );
  }, [confirmMerge, enableMerge, mergeTargetKey, mergingKey, tables]);

  return (
    <div className="flex flex-col min-h-0 flex-1">
      <div className="flex items-center gap-2 px-3 pt-2 border-b border-slate-200 dark:border-slate-700 overflow-x-auto flex-wrap">
        {tables.map((tbl, i) => (
          <div
            key={tbl.localKey}
            className={cn(
              'inline-flex items-center shrink-0 rounded-t border-b-2 -mb-px',
              i === activeIdx
                ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20'
                : 'border-transparent'
            )}
          >
            <button
              type="button"
              onClick={() => setActiveIdx(i)}
              className={cn(
                'px-2.5 py-1.5 text-sm whitespace-nowrap',
                i === activeIdx
                  ? 'text-indigo-700 dark:text-indigo-300 font-medium'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              )}
            >
              Table {tbl.table_index + 1}
            </button>
            {enableReorder && tables.length > 1 && (
              <>
                <button
                  type="button"
                  title="Move earlier (lower index)"
                  disabled={i === 0}
                  onClick={e => {
                    e.stopPropagation();
                    moveTable(i, -1);
                  }}
                  className="p-0.5 text-slate-400 hover:text-slate-700 disabled:opacity-30"
                >
                  <ChevronUp className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  title="Move later (higher index)"
                  disabled={i === tables.length - 1}
                  onClick={e => {
                    e.stopPropagation();
                    moveTable(i, 1);
                  }}
                  className="p-0.5 text-slate-400 hover:text-slate-700 disabled:opacity-30"
                >
                  <ChevronDown className="w-4 h-4" />
                </button>
              </>
            )}
            {enableMerge && tables.length > 1 && (
              <button
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  setMergingKey(tbl.localKey);
                  setMergeTargetKey(null);
                  setActiveIdx(i);
                }}
                className="px-2 py-0.5 mr-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 border border-blue-300 dark:border-blue-600 rounded hover:bg-blue-50 dark:hover:bg-blue-950/40"
              >
                Merge →
              </button>
            )}
            <button
              type="button"
              onClick={e => {
                e.stopPropagation();
                if (mergingKey === tbl.localKey) {
                  setMergingKey(null);
                  setMergeTargetKey(null);
                }
                deleteTableAt(i);
              }}
              className="p-1 mr-0.5 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
              title="Delete table"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addTable}
          className="ml-1 px-2 py-1 text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" /> Add table
        </button>
      </div>

      {mergePanel}

      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-[200px]">
        {t && (
          <>
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
              <table className="text-xs w-full border-collapse min-w-max">
                <thead className="bg-slate-50 dark:bg-slate-800">
                  <tr>
                    <th className="w-8 px-2 py-2 border-b border-slate-200 dark:border-slate-700 text-slate-400">#</th>
                    {t.headers.map((h, ci) => (
                      <th key={ci} className="border-b border-slate-200 dark:border-slate-700 p-0 relative">
                        <div className="flex items-center">
                          <input
                            value={h}
                            onChange={e => setHeader(ci, e.target.value)}
                            className="flex-1 px-2 py-2 bg-transparent font-medium text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20 min-w-[80px]"
                          />
                          {t.headers.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeColumn(ci)}
                              className="px-1 text-slate-300 hover:text-red-500 transition-colors"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </th>
                    ))}
                    <th className="border-b border-slate-200 dark:border-slate-700 w-8">
                      <button type="button" onClick={addColumn} className="px-2 py-2 text-indigo-500 hover:text-indigo-700">
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {t.rows.map((row, ri) => (
                    <tr key={ri} className="group border-b border-slate-100 dark:border-slate-800 last:border-0">
                      <td className="px-2 py-1 text-center text-slate-300 text-[10px]">{ri + 1}</td>
                      {row.map((cell, ci) => (
                        <td key={ci} className="p-0 border-r border-slate-100 dark:border-slate-800 last:border-0">
                          <input
                            value={cell}
                            onChange={e => setCell(ri, ci, e.target.value)}
                            className="w-full px-2 py-1.5 bg-transparent text-slate-700 dark:text-slate-300 focus:outline-none focus:bg-indigo-50 dark:focus:bg-indigo-900/20 min-w-[80px]"
                          />
                        </td>
                      ))}
                      <td className="px-1">
                        <button
                          type="button"
                          onClick={() => removeRow(ri)}
                          className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-red-500 transition-all"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button
              type="button"
              onClick={addRow}
              className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1"
            >
              <Plus className="w-3 h-3" /> Add row
            </button>
          </>
        )}
      </div>
    </div>
  );
}
