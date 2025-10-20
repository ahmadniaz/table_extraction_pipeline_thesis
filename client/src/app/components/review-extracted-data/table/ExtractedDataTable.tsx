/**
 * Extracted Data Table Component
 * Main table component with checkbox selection and inline editing
 */

'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { toast } from 'react-hot-toast';
import { TableData } from '../types';
import { useTableSelection, useSummaryRowDetection, useTableOperations } from '../hooks';
import TableRowSelector from './TableRowSelector';
import TableRow from './TableRow';
import BulkActionsBar from './BulkActionsBar';
import SummaryRowManager from './SummaryRowManager';
import { Plus, Pencil, Trash2, Tag, MoreHorizontal } from 'lucide-react';

interface ExtractedDataTableProps {
  table: TableData;
  onTableChange: (table: TableData) => void;
  showSummaryRows?: boolean;
  onToggleSummaryRows?: () => void;
}

export default function ExtractedDataTable({
  table,
  onTableChange,
  showSummaryRows = true,
  onToggleSummaryRows
}: ExtractedDataTableProps) {
  // Get headers
  const headers = table.header || table.headers || [];
  const totalRows = table.rows.length;

  // Hooks
  const selection = useTableSelection(totalRows);
  const summaryDetection = useSummaryRowDetection(table, onTableChange);
  const operations = useTableOperations(table, onTableChange);

  // Column actions menu state
  const [showColumnActions, setShowColumnActions] = useState<number | null>(null);

  // Get visible rows
  const visibleRows = useMemo(() => {
    if (showSummaryRows) {
      return table.rows.map((row, idx) => ({ row, originalIdx: idx }));
    } else {
      return table.rows
        .map((row, idx) => ({ row, originalIdx: idx }))
        .filter(({ originalIdx }) => !summaryDetection.isSummaryRow(originalIdx));
    }
  }, [table.rows, showSummaryRows, summaryDetection]);

  // Handle cell edit save
  const handleSaveCellEdit = useCallback((rowIndex: number, colIndex: number, value: string) => {
    operations.editCell(rowIndex, colIndex, value);
    toast.success('Cell updated');
  }, [operations]);

  // Handle bulk delete
  const handleDeleteSelected = useCallback(() => {
    const selectedIndices = Array.from(selection.selectedRows).sort((a, b) => b - a);
    if (selectedIndices.length === 0) return;

    operations.deleteRows(selectedIndices);
    selection.clearSelection();
    toast.success(`Deleted ${selectedIndices.length} row(s)`);
  }, [selection, operations]);

  // Handle mark as summary
  const handleMarkAsSummary = useCallback(() => {
    const selectedIndices = Array.from(selection.selectedRows);
    selectedIndices.forEach(idx => {
      summaryDetection.markAsSummaryRow(idx);
    });
    selection.clearSelection();
    toast.success(`Marked ${selectedIndices.length} row(s) as summary`);
  }, [selection, summaryDetection]);

  // Handle auto-detect summary rows
  const handleAutoDetect = useCallback(() => {
    const count = summaryDetection.autoDetectSummaryRows();
    toast.success(`Auto-detected ${count} summary row(s)`);
  }, [summaryDetection]);

  // Handle row actions
  const handleAddRowAbove = useCallback((rowIndex: number) => {
    operations.addRow(rowIndex);
    toast.success('Row added above');
  }, [operations]);

  const handleAddRowBelow = useCallback((rowIndex: number) => {
    operations.addRow(rowIndex + 1);
    toast.success('Row added below');
  }, [operations]);

  const handleDeleteRow = useCallback((rowIndex: number) => {
    operations.deleteRow(rowIndex);
    toast.success('Row deleted');
  }, [operations]);

  const handleToggleSummary = useCallback((rowIndex: number) => {
    if (summaryDetection.isSummaryRow(rowIndex)) {
      summaryDetection.unmarkSummaryRow(rowIndex);
      toast.success('Unmarked as summary row');
    } else {
      summaryDetection.markAsSummaryRow(rowIndex);
      toast.success('Marked as summary row');
    }
  }, [summaryDetection]);

  // Column action handlers
  const handleRenameColumn = useCallback((colIndex: number, newName: string) => {
    operations.renameColumn(colIndex, newName);
    setShowColumnActions(null);
    toast.success('Column renamed');
  }, [operations]);

  const handleAddColumnAfter = useCallback((colIndex: number) => {
    operations.addColumn(colIndex + 1);
    setShowColumnActions(null);
    toast.success('Column added');
  }, [operations]);

  const handleDeleteColumn = useCallback((colIndex: number) => {
    operations.deleteColumn(colIndex);
    setShowColumnActions(null);
    toast.success('Column deleted');
  }, [operations]);

  return (
    <div className="flex flex-col h-full w-full bg-gray-50 dark:bg-slate-900">
      {/* Table Controls */}
      <div className="flex items-center justify-between px-6 py-4 border-b-2 border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Table Data ({visibleRows.length} rows)
          </h3>
        </div>
      </div>

      {/* Table - Fixed container width with internal scroll */}
      <div className="flex-1 overflow-x-auto overflow-y-auto w-full min-w-0 bg-white dark:bg-slate-800">
        <table className="w-max min-w-full border-collapse company-table">
          <thead className="sticky top-0 z-10 bg-gray-50 dark:bg-slate-700">
            <tr>
              {/* Select All Checkbox */}
              <th className="px-4 py-3 text-left w-12 border-b border-gray-200 dark:border-slate-700 border-r border-gray-200 dark:border-slate-700 sticky left-0 bg-gray-50 dark:bg-slate-700 z-20">
                <TableRowSelector
                  isSelected={selection.isAllSelected}
                  isIndeterminate={selection.isIndeterminate}
                  onToggle={selection.toggleAllRowsSelection}
                  ariaLabel="Select all rows"
                />
              </th>

              {/* Column Headers */}
              {headers.map((header, colIdx) => (
                <th
                  key={colIdx}
                  className="px-3 py-3 text-left text-xs font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-700 border-r border-gray-200 dark:border-slate-700 whitespace-nowrap relative group min-w-[150px]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{header}</span>
                    <button
                      onClick={() => setShowColumnActions(showColumnActions === colIdx ? null : colIdx)}
                      className="p-1 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded transition-colors flex-shrink-0"
                      title="Column actions"
                    >
                      <MoreHorizontal size={12} />
                    </button>
                  </div>

                  {/* Column Actions Menu */}
                  {showColumnActions === colIdx && (
                    <ColumnActionMenu
                      colIndex={colIdx}
                      header={header}
                      isFirstColumn={colIdx < 2}
                      onRename={handleRenameColumn}
                      onAddAfter={handleAddColumnAfter}
                      onDelete={handleDeleteColumn}
                      onClose={() => setShowColumnActions(null)}
                    />
                  )}
                </th>
              ))}

              {/* Actions Column */}
              <th className="px-3 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 border-r border-slate-200 dark:border-slate-700 w-12">
                Actions
              </th>
            </tr>
          </thead>

          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td
                  colSpan={headers.length + 2}
                  className="px-4 py-8 text-center text-gray-500 dark:text-slate-400"
                >
                  No rows available
                </td>
              </tr>
            ) : (
              visibleRows.map(({ row, originalIdx }) => (
                <TableRow
                  key={originalIdx}
                  row={row}
                  rowIndex={originalIdx}
                  isSelected={selection.isRowSelected(originalIdx)}
                  isSummary={summaryDetection.isSummaryRow(originalIdx)}
                  editingCell={operations.editingCell}
                  onToggleSelection={selection.toggleRowSelection}
                  onStartCellEdit={operations.startCellEdit}
                  onSaveCellEdit={handleSaveCellEdit}
                  onCancelCellEdit={operations.cancelCellEdit}
                  onAddRowAbove={handleAddRowAbove}
                  onAddRowBelow={handleAddRowBelow}
                  onToggleSummary={handleToggleSummary}
                  onDeleteRow={handleDeleteRow}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selection.selectedRows.size}
        onDeleteSelected={handleDeleteSelected}
        onMarkAsSummary={handleMarkAsSummary}
        onClearSelection={selection.clearSelection}
      />
    </div>
  );
}

// Column Action Menu Component
interface ColumnActionMenuProps {
  colIndex: number;
  header: string;
  isFirstColumn?: boolean;
  onRename: (colIndex: number, newName: string) => void;
  onAddAfter: (colIndex: number) => void;
  onDelete: (colIndex: number) => void;
  onClose: () => void;
}

function ColumnActionMenu({
  colIndex,
  header,
  isFirstColumn = false,
  onRename,
  onAddAfter,
  onDelete,
  onClose
}: ColumnActionMenuProps) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [newName, setNewName] = useState(header);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[100]"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
      />

      {/* Menu - Position left for first columns to avoid hiding under preview */}
      <div
        className={`absolute top-full mt-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg shadow-2xl z-[101] min-w-[200px] max-h-[300px] overflow-y-auto ${
          isFirstColumn ? 'left-0' : 'right-0'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-2 border-b border-slate-100 dark:border-slate-700">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-300">Column Actions</div>
        </div>

        {isRenaming ? (
          <div className="p-3">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && newName.trim()) {
                  onRename(colIndex, newName.trim());
                  setIsRenaming(false);
                }
                if (e.key === 'Escape') {
                  setIsRenaming(false);
                }
              }}
              className="w-full px-2 py-1 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded text-sm focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
              placeholder="New column name"
              autoFocus
            />
            <div className="flex gap-1 mt-2">
              <button
                onClick={() => {
                  if (newName.trim()) {
                    onRename(colIndex, newName.trim());
                    setIsRenaming(false);
                  }
                }}
                className="px-2 py-1 bg-slate-600 dark:bg-slate-700 text-white rounded text-xs hover:bg-slate-700 dark:hover:bg-slate-600"
              >
                Save
              </button>
              <button
                onClick={() => setIsRenaming(false)}
                className="px-2 py-1 bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-300 rounded text-xs hover:bg-slate-400 dark:hover:bg-slate-500"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            <button
              onClick={() => setIsRenaming(true)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
            >
              <Pencil className="w-4 h-4" />
              Rename Column
            </button>

            <button
              onClick={() => onAddAfter(colIndex)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
            >
              <Plus className="w-4 h-4" />
              Add Column After
            </button>

            <div className="border-t border-slate-100 dark:border-slate-700 my-1" />

            <button
              onClick={() => onDelete(colIndex)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete Column
            </button>
          </div>
        )}
      </div>
    </>
  );
}

