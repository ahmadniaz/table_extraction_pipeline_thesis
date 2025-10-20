/**
 * Table Selection Hook
 * Handles row selection state with optimal performance
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import { TableSelectionState, TableSelectionActions } from '../types';

export function useTableSelection(totalRows: number) {
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());

  // Calculate selection state
  const selectionState: TableSelectionState = useMemo(() => {
    const isAllSelected = totalRows > 0 && selectedRows.size === totalRows;
    const isIndeterminate = selectedRows.size > 0 && selectedRows.size < totalRows;

    return {
      selectedRows,
      isAllSelected,
      isIndeterminate
    };
  }, [selectedRows, totalRows]);

  // Toggle individual row selection
  const toggleRowSelection = useCallback((rowIndex: number) => {
    setSelectedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rowIndex)) {
        newSet.delete(rowIndex);
      } else {
        newSet.add(rowIndex);
      }
      return newSet;
    });
  }, []);

  // Toggle all rows selection
  const toggleAllRowsSelection = useCallback(() => {
    setSelectedRows(prev => {
      if (prev.size === totalRows) {
        return new Set(); // Deselect all
      } else {
        // Select all
        const newSet = new Set<number>();
        for (let i = 0; i < totalRows; i++) {
          newSet.add(i);
        }
        return newSet;
      }
    });
  }, [totalRows]);

  // Clear all selections
  const clearSelection = useCallback(() => {
    setSelectedRows(new Set());
  }, []);

  // Select a range of rows (for shift+click support)
  const selectRowRange = useCallback((startIndex: number, endIndex: number) => {
    setSelectedRows(prev => {
      const newSet = new Set(prev);
      const min = Math.min(startIndex, endIndex);
      const max = Math.max(startIndex, endIndex);
      for (let i = min; i <= max; i++) {
        newSet.add(i);
      }
      return newSet;
    });
  }, []);

  // Check if a row is selected
  const isRowSelected = useCallback((rowIndex: number) => {
    return selectedRows.has(rowIndex);
  }, [selectedRows]);

  const actions: TableSelectionActions = {
    toggleRowSelection,
    toggleAllRowsSelection,
    clearSelection,
    selectRowRange,
    isRowSelected
  };

  return {
    ...selectionState,
    ...actions
  };
}

