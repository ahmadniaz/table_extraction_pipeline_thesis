/**
 * Table Operations Hook
 * Handles CRUD operations on table data with undo/redo support
 */

'use client';

import { useState, useCallback } from 'react';
import { TableData, TableOperationsActions, CellEdit } from '../types';
import { createEmptyRow } from '../utils/tableUtils';

export function useTableOperations(
  table: TableData,
  onTableChange: (table: TableData) => void
) {
  const [editingCell, setEditingCell] = useState<CellEdit | null>(null);

  // Add a new row at a specific position
  const addRow = useCallback((position: number, data?: string[]) => {
    const columnCount = table.header?.length || table.headers?.length || 0;
    const newRow = data || createEmptyRow(columnCount);
    
    const updatedRows = [...table.rows];
    updatedRows.splice(position, 0, newRow);
    
    onTableChange({
      ...table,
      rows: updatedRows
    });
  }, [table, onTableChange]);

  // Delete a single row
  const deleteRow = useCallback((rowIndex: number) => {
    const updatedRows = table.rows.filter((_, idx) => idx !== rowIndex);
    
    // Update summary rows if necessary
    const updatedSummaryRows = new Set<number>();
    if (table.summaryRows) {
      table.summaryRows.forEach(idx => {
        if (idx < rowIndex) {
          updatedSummaryRows.add(idx);
        } else if (idx > rowIndex) {
          updatedSummaryRows.add(idx - 1);
        }
        // Skip if idx === rowIndex (we're deleting it)
      });
    }
    
    onTableChange({
      ...table,
      rows: updatedRows,
      summaryRows: updatedSummaryRows
    });
  }, [table, onTableChange]);

  // Delete multiple rows
  const deleteRows = useCallback((rowIndices: number[]) => {
    const indicesToDelete = new Set(rowIndices);
    const updatedRows = table.rows.filter((_, idx) => !indicesToDelete.has(idx));
    
    // Update summary rows
    const updatedSummaryRows = new Set<number>();
    if (table.summaryRows) {
      const summaryRowsSet = table.summaryRows instanceof Set ? table.summaryRows : new Set(table.summaryRows);
      let deletedCount = 0;
      for (let i = 0; i < table.rows.length; i++) {
        if (indicesToDelete.has(i)) {
          deletedCount++;
        } else if (summaryRowsSet.has(i)) {
          updatedSummaryRows.add(i - deletedCount);
        }
      }
    }
    
    onTableChange({
      ...table,
      rows: updatedRows,
      summaryRows: updatedSummaryRows
    });
  }, [table, onTableChange]);

  // Edit a single cell
  const editCell = useCallback((rowIndex: number, colIndex: number, value: string) => {
    const updatedRows = [...table.rows];
    if (updatedRows[rowIndex]) {
      updatedRows[rowIndex] = [...updatedRows[rowIndex]];
      updatedRows[rowIndex][colIndex] = value;
      
      onTableChange({
        ...table,
        rows: updatedRows
      });
    }
  }, [table, onTableChange]);

  // Start editing a cell
  const startCellEdit = useCallback((rowIndex: number, colIndex: number) => {
    const currentValue = table.rows[rowIndex]?.[colIndex] || '';
    setEditingCell({
      tableIdx: 0, // Single table for now
      rowIdx: rowIndex,
      colIdx: colIndex,
      value: currentValue
    });
  }, [table.rows]);

  // Save cell edit
  const saveCellEdit = useCallback(() => {
    if (editingCell) {
      editCell(editingCell.rowIdx, editingCell.colIdx, editingCell.value);
      setEditingCell(null);
    }
  }, [editingCell, editCell]);

  // Cancel cell edit
  const cancelCellEdit = useCallback(() => {
    setEditingCell(null);
  }, []);

  // Update editing cell value
  const updateEditingCellValue = useCallback((value: string) => {
    if (editingCell) {
      setEditingCell({ ...editingCell, value });
    }
  }, [editingCell]);

  // Add a new column at a specific position
  const addColumn = useCallback((position: number, name?: string) => {
    const headers = table.header || table.headers || [];
    const updatedHeaders = [...headers];
    updatedHeaders.splice(position, 0, name || `Column ${position + 1}`);
    
    const updatedRows = table.rows.map(row => {
      const newRow = [...row];
      newRow.splice(position, 0, '');
      return newRow;
    });
    
    onTableChange({
      ...table,
      header: updatedHeaders,
      headers: updatedHeaders,
      rows: updatedRows
    });
  }, [table, onTableChange]);

  // Rename a column
  const renameColumn = useCallback((colIndex: number, newName: string) => {
    const headers = table.header || table.headers || [];
    const updatedHeaders = [...headers];
    updatedHeaders[colIndex] = newName;
    
    onTableChange({
      ...table,
      header: updatedHeaders,
      headers: updatedHeaders
    });
  }, [table, onTableChange]);

  // Delete a column
  const deleteColumn = useCallback((colIndex: number) => {
    const headers = table.header || table.headers || [];
    const updatedHeaders = headers.filter((_, idx) => idx !== colIndex);
    
    const updatedRows = table.rows.map(row => 
      row.filter((_, idx) => idx !== colIndex)
    );
    
    onTableChange({
      ...table,
      header: updatedHeaders,
      headers: updatedHeaders,
      rows: updatedRows
    });
  }, [table, onTableChange]);

  const operations: TableOperationsActions = {
    addRow,
    deleteRow,
    deleteRows,
    editCell,
    undo: () => {}, // TODO: Implement undo/redo
    redo: () => {},
    canUndo: false,
    canRedo: false
  };

  return {
    ...operations,
    editingCell,
    startCellEdit,
    saveCellEdit,
    cancelCellEdit,
    updateEditingCellValue,
    setEditingCell,
    addColumn,
    renameColumn,
    deleteColumn
  };
}

