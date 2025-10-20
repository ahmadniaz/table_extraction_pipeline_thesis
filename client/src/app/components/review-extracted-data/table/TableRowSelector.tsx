/**
 * Table Row Selector Component
 * Optimized checkbox component for row selection
 */

'use client';

import React, { memo, useCallback } from 'react';

interface TableRowSelectorProps {
  isSelected: boolean;
  isIndeterminate?: boolean;
  onToggle: () => void;
  ariaLabel?: string;
}

const TableRowSelector = memo(function TableRowSelector({
  isSelected,
  isIndeterminate = false,
  onToggle,
  ariaLabel = 'Select row'
}: TableRowSelectorProps) {
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onToggle();
  }, [onToggle]);

  return (
    <label
      className="cursor-pointer flex items-center justify-center w-full h-full"
      onClick={handleClick}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={() => {}}
        ref={(input) => {
          if (input) {
            input.indeterminate = isIndeterminate;
          }
        }}
        className="w-4 h-4 text-blue-600 dark:text-blue-400 rounded border-gray-300 dark:border-slate-600 focus:ring-blue-500 focus:ring-2 cursor-pointer accent-blue-600"
        aria-label={ariaLabel}
      />
    </label>
  );
});

export default TableRowSelector;

