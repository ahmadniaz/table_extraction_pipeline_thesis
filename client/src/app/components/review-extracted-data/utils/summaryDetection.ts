/**
 * Summary Row Detection Algorithms
 * Smart pattern matching for identifying summary rows
 */

import { TableData } from '../types';

// Summary keywords for pattern matching
const SUMMARY_KEYWORDS = [
  'total',
  'subtotal',
  'summary',
  'group',
  'grand',
  'sum',
  'count',
  'amount',
  'balance',
  'net',
  'final',
  'overall',
  'combined',
  'aggregate'
];

// Summary patterns for regex matching
const SUMMARY_PATTERNS = [
  /^total for group:?\s*[a-z\s]+$/i,
  /^total:?\s*[a-z\s]*$/i,
  /^subtotal:?\s*[a-z\s]*$/i,
  /^summary:?\s*[a-z\s]*$/i,
  /^grand total:?\s*[a-z\s]*$/i,
  /^group total:?\s*[a-z\s]*$/i,
  /^[a-z\s]+\s+total$/i,
  /^total\s+[a-z\s]+$/i
];

/**
 * Calculate similarity score between two rows (0-1)
 */
export function calculateRowSimilarity(row1: string[], row2: string[]): number {
  if (row1.length !== row2.length) return 0;

  let matchingCells = 0;
  const totalCells = row1.length;

  for (let i = 0; i < row1.length; i++) {
    const cell1 = (row1[i] || '').trim().toLowerCase();
    const cell2 = (row2[i] || '').trim().toLowerCase();

    if (cell1 === cell2 && cell1 !== '') {
      matchingCells++;
    } else if (cell1 === '' && cell2 === '') {
      matchingCells++;
    }
  }

  return totalCells > 0 ? matchingCells / totalCells : 0;
}

/**
 * Check if a row contains summary keywords
 */
function hasSummaryKeywords(row: string[]): boolean {
  const firstCells = row.slice(0, 3).map(cell => (cell || '').trim().toLowerCase());
  return firstCells.some(cell => 
    SUMMARY_KEYWORDS.some(keyword => cell.includes(keyword))
  );
}

/**
 * Check if a row matches summary patterns
 */
function matchesSummaryPattern(row: string[]): boolean {
  const firstCell = (row[0] || '').trim();
  return SUMMARY_PATTERNS.some(pattern => pattern.test(firstCell));
}

/**
 * Check if a row has numeric values (typical for summary rows)
 */
function hasNumericValues(row: string[]): boolean {
  return row.slice(2, 6).some(cell => {
    const cellValue = (cell || '').trim();
    return /^\$?[\d,]+\.?\d*$/.test(cellValue) || /^\d+$/.test(cellValue);
  });
}

/**
 * Find similar rows to a reference row (for pattern-based detection)
 */
export function findSimilarRows(
  table: TableData,
  targetRow: string[],
  targetRowIdx: number,
  similarityThreshold = 0.7
): number[] {
  const similarRows: number[] = [];
  const targetFirstCells = targetRow.slice(0, 3).map(cell => (cell || '').trim().toLowerCase());
  const isTargetSummaryRow = hasSummaryKeywords(targetRow);

  if (isTargetSummaryRow) {
    // For summary rows, look for similar patterns
    table.rows.forEach((row, rowIdx) => {
      if (rowIdx === targetRowIdx) return;

      const rowFirstCells = row.slice(0, 3).map(cell => (cell || '').trim().toLowerCase());
      const isRowSummaryRow = hasSummaryKeywords(row);

      if (isRowSummaryRow) {
        // Check for specific pattern matching
        let isSimilar = false;

        // Check for matching summary patterns
        const targetKeyword = SUMMARY_KEYWORDS.find(keyword => targetFirstCells[0].includes(keyword));
        const rowKeyword = SUMMARY_KEYWORDS.find(keyword => rowFirstCells[0].includes(keyword));

        if (targetKeyword && rowKeyword && targetKeyword === rowKeyword) {
          isSimilar = true;
        }

        if (isSimilar) {
          similarRows.push(rowIdx);
        }
      }
    });
  } else {
    // For regular rows, use similarity calculation
    table.rows.forEach((row, rowIdx) => {
      if (rowIdx === targetRowIdx) return;

      const similarity = calculateRowSimilarity(targetRow, row);
      if (similarity >= similarityThreshold) {
        similarRows.push(rowIdx);
      }
    });
  }

  return similarRows;
}

/**
 * Automatically detect summary rows in a table
 */
export function autoDetectSummaryRows(table: TableData): number[] {
  const detectedRows: number[] = [];

  table.rows.forEach((row, rowIdx) => {
    if (!row || row.length === 0) return;

    // Strategy 1: Check for exact pattern matches
    if (matchesSummaryPattern(row)) {
      detectedRows.push(rowIdx);
      return;
    }

    // Strategy 2: Check for summary keywords + numeric values
    if (hasSummaryKeywords(row) && hasNumericValues(row)) {
      detectedRows.push(rowIdx);
      return;
    }

    // Strategy 3: Check for "Total for Group:" pattern specifically
    const firstCell = (row[0] || '').trim().toLowerCase();
    if (firstCell.includes('total for group')) {
      detectedRows.push(rowIdx);
      return;
    }
  });

  return detectedRows;
}

/**
 * Check if a specific row is a summary row
 */
export function isSummaryRow(table: TableData, rowIdx: number): boolean {
  if (!table?.summaryRows) return false;
  
  // Handle both Set and Array (for backward compatibility)
  if (table.summaryRows instanceof Set) {
    return table.summaryRows.has(rowIdx);
  }
  
  // If it's an array, convert to Set check
  if (Array.isArray(table.summaryRows)) {
    return (table.summaryRows as number[]).includes(rowIdx);
  }
  
  return false;
}

