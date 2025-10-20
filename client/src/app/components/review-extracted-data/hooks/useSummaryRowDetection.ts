/**
 * Summary Row Detection Hook
 * Handles summary row marking and pattern detection
 */

'use client';

import { useState, useCallback } from 'react';
import { TableData, SummaryRowDetection } from '../types';
import { 
  autoDetectSummaryRows, 
  findSimilarRows, 
  isSummaryRow as checkIsSummaryRow 
} from '../utils/summaryDetection';

export function useSummaryRowDetection(
  table: TableData,
  onTableChange: (table: TableData) => void
) {
  // Ensure summaryRows is always a Set
  const summaryRows = table.summaryRows 
    ? (Array.isArray(table.summaryRows) ? new Set(table.summaryRows) : table.summaryRows)
    : new Set<number>();

  // Mark a row as summary row
  const markAsSummaryRow = useCallback((rowIndex: number) => {
    const updatedTable = {
      ...table,
      summaryRows: new Set(summaryRows).add(rowIndex)
    };
    onTableChange(updatedTable);
  }, [table, summaryRows, onTableChange]);

  // Unmark a summary row
  const unmarkSummaryRow = useCallback((rowIndex: number) => {
    const newSummaryRows = new Set(summaryRows);
    newSummaryRows.delete(rowIndex);
    const updatedTable = {
      ...table,
      summaryRows: newSummaryRows
    };
    onTableChange(updatedTable);
  }, [table, summaryRows, onTableChange]);

  // Detect similar rows based on a reference row
  const detectSimilarRows = useCallback((referenceRowIndex: number) => {
    const referenceRow = table.rows[referenceRowIndex];
    if (!referenceRow) return [];
    
    return findSimilarRows(table, referenceRow, referenceRowIndex);
  }, [table]);

  // Auto-detect all summary rows in the table
  const autoDetect = useCallback(() => {
    const detectedIndices = autoDetectSummaryRows(table);
    const newSummaryRows = new Set([...summaryRows, ...detectedIndices]);
    const updatedTable = {
      ...table,
      summaryRows: newSummaryRows
    };
    onTableChange(updatedTable);
    return detectedIndices.length;
  }, [table, summaryRows, onTableChange]);

  // Check if a row is a summary row
  const isSummary = useCallback((rowIndex: number) => {
    return checkIsSummaryRow(table, rowIndex);
  }, [table]);

  const detection: SummaryRowDetection = {
    summaryRows,
    markAsSummaryRow,
    unmarkSummaryRow,
    detectSimilarRows,
    autoDetectSummaryRows: autoDetect,
    isSummaryRow: isSummary
  };

  return detection;
}

