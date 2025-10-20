/**
 * Table Utility Functions
 * Helper functions for table operations and data validation
 */

import { DataType, ValidationResult } from '../types';

/**
 * Detect the data type of a cell value
 */
export function detectDataType(value: string): DataType {
  if (!value || value.trim() === '') return 'empty';

  const trimmed = value.trim();

  // Check for currency
  if (/^\$[\d,]+\.?\d*$/.test(trimmed) || /^\(\$[\d,]+\.?\d*\)$/.test(trimmed) || /[\$€£¥₹]/.test(trimmed)) {
    return 'currency';
  }

  // Check for percentage
  if (/^\d+\.?\d*%$/.test(trimmed)) {
    return 'percentage';
  }

  // Check for date
  if (
    /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(trimmed) ||
    /^\d{4}-\d{1,2}-\d{1,2}$/.test(trimmed) ||
    /^\d{1,2}-\d{1,2}-\d{4}$/.test(trimmed)
  ) {
    return 'date';
  }

  // Check for number
  if (/^-?\d+\.?\d*$/.test(trimmed) || /^\(\d+\.?\d*\)$/.test(trimmed)) {
    return 'number';
  }

  return 'text';
}

/**
 * Validate row format against a reference row
 */
export function validateRowFormat(referenceRow: string[], targetRow: string[]): ValidationResult {
  const issues: string[] = [];
  const maxCols = Math.max(referenceRow.length, targetRow.length);

  for (let i = 0; i < maxCols; i++) {
    const refValue = referenceRow[i] || '';
    const targetValue = targetRow[i] || '';

    if (refValue.trim() === '') continue;

    const refDataType = detectDataType(refValue);
    const targetDataType = detectDataType(targetValue);

    if (targetDataType === 'empty') continue;

    if (refDataType !== targetDataType) {
      issues.push(`Column ${i + 1}: Expected ${refDataType}, got ${targetDataType} (${targetValue})`);
    }
  }

  return {
    isValid: issues.length === 0,
    issues
  };
}

/**
 * Clean duplicate column names (e.g., "Name.Name" -> "Name")
 */
export function cleanColumnNames(headers: string[]): string[] {
  return headers.map(header => {
    if (header.includes('.')) {
      const parts = header.split('.');
      if (parts.length === 2 && parts[0].trim() === parts[1].trim()) {
        return parts[0].trim();
      }
    }
    return header;
  });
}

/**
 * Generate a unique row ID
 */
export function generateRowId(): string {
  return `row_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Create an empty row with the correct number of columns
 */
export function createEmptyRow(columnCount: number): string[] {
  return Array(columnCount).fill('');
}

/**
 * Check if a row is completely empty
 */
export function isEmptyRow(row: string[]): boolean {
  return row.every(cell => !cell || cell.trim() === '');
}

/**
 * Deep clone a table data structure
 */
export function cloneTable<T>(data: T): T {
  return JSON.parse(JSON.stringify(data));
}

/**
 * Format a number as currency
 */
export function formatCurrency(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value;
  if (isNaN(num)) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(num);
}

/**
 * Parse currency string to number
 */
export function parseCurrency(value: string): number {
  const num = parseFloat(value.replace(/[^0-9.-]/g, ''));
  return isNaN(num) ? 0 : num;
}

/**
 * Get visible row indices (excluding summary rows if needed)
 */
export function getVisibleRowIndices(
  totalRows: number,
  summaryRows: Set<number>,
  showSummaryRows: boolean
): number[] {
  const indices: number[] = [];
  for (let i = 0; i < totalRows; i++) {
    if (showSummaryRows || !summaryRows.has(i)) {
      indices.push(i);
    }
  }
  return indices;
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  return function(...args: Parameters<T>) {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

