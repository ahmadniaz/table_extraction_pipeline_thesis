/**
 * Table Types for Review Extracted Data Component
 */

export interface TableData {
  header: string[];
  headers?: string[]; // Backward compatibility
  rows: string[][];
  name?: string;
  id?: string;
  extractor?: string;
  metadata?: {
    extraction_method?: string;
    [key: string]: any;
  };
  summaryRows?: Set<number> | number[]; // Support both Set and Array for backward compatibility
}

export interface CellEdit {
  tableIdx: number;
  rowIdx: number;
  colIdx: number;
  value: string;
}

export interface RowEdit {
  tableIdx: number;
  rowIdx: number;
  values: string[];
}

export interface TableSelectionState {
  selectedRows: Set<number>;
  isAllSelected: boolean;
  isIndeterminate: boolean;
}

export interface TableSelectionActions {
  toggleRowSelection: (rowIndex: number) => void;
  toggleAllRowsSelection: () => void;
  clearSelection: () => void;
  selectRowRange: (startIndex: number, endIndex: number) => void;
  isRowSelected: (rowIndex: number) => boolean;
}

export interface SummaryRowDetection {
  summaryRows: Set<number>;
  markAsSummaryRow: (rowIndex: number) => void;
  unmarkSummaryRow: (rowIndex: number) => void;
  detectSimilarRows: (referenceRowIndex: number) => number[];
  autoDetectSummaryRows: () => void;
  isSummaryRow: (rowIndex: number) => boolean;
}

export interface TableOperation {
  type: 'add_row' | 'delete_row' | 'edit_cell' | 'edit_row' | 'add_column' | 'delete_column';
  timestamp: number;
  data: any;
}

export interface TableOperationsState {
  history: TableOperation[];
  currentIndex: number;
}

export interface TableOperationsActions {
  addRow: (position: number, data?: string[]) => void;
  deleteRow: (rowIndex: number) => void;
  deleteRows: (rowIndices: number[]) => void;
  editCell: (rowIndex: number, colIndex: number, value: string) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export type DataType = 'text' | 'number' | 'date' | 'currency' | 'percentage' | 'empty';

export interface ValidationResult {
  isValid: boolean;
  issues: string[];
}

