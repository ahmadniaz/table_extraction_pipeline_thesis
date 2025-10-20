/**
 * Table Row Component
 * Optimized row component with memoization for performance
 */

'use client';

import React, { memo, useCallback, useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import TableRowSelector from './TableRowSelector';
import EditableCell from './EditableCell';
import { MoreVertical, Plus, Tag, Trash2 } from 'lucide-react';

interface TableRowProps {
  row: string[];
  rowIndex: number;
  isSelected: boolean;
  isSummary: boolean;
  editingCell: { rowIdx: number; colIdx: number } | null;
  onToggleSelection: (rowIndex: number) => void;
  onStartCellEdit: (rowIndex: number, colIndex: number) => void;
  onSaveCellEdit: (rowIndex: number, colIndex: number, value: string) => void;
  onCancelCellEdit: () => void;
  onAddRowAbove: (rowIndex: number) => void;
  onAddRowBelow: (rowIndex: number) => void;
  onToggleSummary: (rowIndex: number) => void;
  onDeleteRow: (rowIndex: number) => void;
}

const TableRow = memo(function TableRow({
  row,
  rowIndex,
  isSelected,
  isSummary,
  editingCell,
  onToggleSelection,
  onStartCellEdit,
  onSaveCellEdit,
  onCancelCellEdit,
  onAddRowAbove,
  onAddRowBelow,
  onToggleSummary,
  onDeleteRow
}: TableRowProps) {
  const [showActions, setShowActions] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  
  const rowRef = useRef<HTMLTableRowElement>(null);
  const actionsButtonRef = useRef<HTMLButtonElement>(null);
  const actionsMenuRef = useRef<HTMLDivElement>(null);

  const handleToggle = useCallback(() => {
    onToggleSelection(rowIndex);
  }, [rowIndex, onToggleSelection]);

  // Calculate dropdown position to avoid overlapping
  const calculateDropdownPosition = useCallback(() => {
    if (!actionsButtonRef.current) return;
    
    const buttonRect = actionsButtonRef.current.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const dropdownHeight = 250; // Approximate dropdown height
    const dropdownWidth = 200; // Approximate dropdown width
    
    let top = buttonRect.bottom + window.scrollY;
    let left = buttonRect.left + window.scrollX;
    
    // Adjust if dropdown would go below viewport
    if (buttonRect.bottom + dropdownHeight > viewportHeight) {
      top = buttonRect.top + window.scrollY - dropdownHeight;
    }
    
    // Adjust if dropdown would go beyond right edge
    if (buttonRect.left + dropdownWidth > viewportWidth) {
      left = buttonRect.right + window.scrollX - dropdownWidth;
    }
    
    setDropdownPosition({ top, left });
  }, []);

  const handleActionsToggle = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!showActions) {
      calculateDropdownPosition();
    }
    setShowActions(!showActions);
  }, [showActions, calculateDropdownPosition]);

  // Close menu when clicking outside
  useEffect(() => {
    if (!showActions) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      
      // Don't close if clicking the button or menu
      if (
        actionsButtonRef.current?.contains(target) ||
        actionsMenuRef.current?.contains(target)
      ) {
        return;
      }
      
      setShowActions(false);
    };

    // Use capture phase to ensure we intercept the event
    document.addEventListener('mousedown', handleClickOutside, true);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true);
    };
  }, [showActions]);

  // Close on Escape key
  useEffect(() => {
    if (!showActions) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowActions(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [showActions]);

  // Recalculate position on scroll or resize
  useEffect(() => {
    if (!showActions) return;

    const handlePositionUpdate = () => {
      calculateDropdownPosition();
    };

    window.addEventListener('scroll', handlePositionUpdate, true);
    window.addEventListener('resize', handlePositionUpdate);
    
    return () => {
      window.removeEventListener('scroll', handlePositionUpdate, true);
      window.removeEventListener('resize', handlePositionUpdate);
    };
  }, [showActions, calculateDropdownPosition]);

  // Action handlers with menu closing
  const handleAction = useCallback((action: () => void) => {
    return (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      action();
      setShowActions(false);
    };
  }, []);

  return (
    <>
      <tr
        ref={rowRef}
        className={`
          relative table-row-hover hover:bg-slate-50 dark:hover:bg-slate-800
          ${isSelected ? 'selected bg-slate-50/50 dark:bg-slate-800/30 border-l-4 border-l-blue-500 dark:border-l-blue-400 hover:bg-slate-100 dark:hover:bg-slate-700/40' : ''}
          ${isSummary ? 'summary-row bg-orange-50 dark:bg-orange-900/30 border-l-4 border-l-orange-500' : ''}
          ${showActions ? 'table-row-actions-active z-10' : ''}
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Checkbox Cell - Fixed position on left */}
        <td className={`px-1 py-1 w-10 border-b border-gray-200 dark:border-slate-700 border-r border-gray-200 dark:border-slate-700 sticky left-0 z-20 shadow-[2px_0_4px_rgba(0,0,0,0.05)] dark:shadow-[2px_0_4px_rgba(0,0,0,0.2)] ${
          isSelected 
            ? 'bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-100 dark:hover:bg-slate-700/40' 
            : isSummary 
              ? 'bg-orange-50 dark:bg-orange-900/30' 
              : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
        }`}>
          <TableRowSelector
            isSelected={isSelected}
            onToggle={handleToggle}
            ariaLabel={`Select row ${rowIndex + 1}`}
          />
        </td>

        {/* Data Cells */}
        {row.map((cell, colIndex) => (
          <td key={colIndex} className={`px-1 py-1 text-xs text-gray-900 dark:text-slate-100 border-b border-gray-100 dark:border-slate-700 border-r border-gray-100 dark:border-slate-700 min-w-[150px] hover:bg-slate-50 dark:hover:bg-slate-800 ${
            isSelected ? 'bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-100 dark:hover:bg-slate-700/40' : ''
          }`}>
            <EditableCell
              value={cell}
              isEditing={
                editingCell?.rowIdx === rowIndex && editingCell?.colIdx === colIndex
              }
              onStartEdit={() => onStartCellEdit(rowIndex, colIndex)}
              onSave={(value) => onSaveCellEdit(rowIndex, colIndex, value)}
              onCancel={onCancelCellEdit}
            />
          </td>
        ))}

        {/* Actions Cell - Fixed position on right */}
        <td className={`px-1 py-1 w-12 relative border-b border-gray-100 dark:border-slate-700 border-r border-gray-100 dark:border-slate-700 sticky right-0 z-20 shadow-[-2px_0_4px_rgba(0,0,0,0.05)] dark:shadow-[-2px_0_4px_rgba(0,0,0,0.2)] ${
          isSelected 
            ? 'bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-100 dark:hover:bg-slate-700/40' 
            : isSummary 
              ? 'bg-orange-50 dark:bg-orange-900/30'
              : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
        }`}>
          <div className="flex items-center justify-center">
            <button
              ref={actionsButtonRef}
              onClick={handleActionsToggle}
              className={`
                p-1.5 rounded transition-all duration-150 ease-out
                relative z-10
                ${showActions
                  ? 'text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700/50 shadow-sm'
                  : isSelected 
                    ? 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50'
                    : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                }
              `}
              title="Row actions"
              aria-expanded={showActions}
              aria-haspopup="menu"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </td>
      </tr>

      {/* Portal-based Dropdown Menu */}
      {showActions && typeof window !== 'undefined' && (
        createPortal(
          <div
            ref={actionsMenuRef}
            className="fixed bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 py-2 min-w-[180px] animate-fadeIn"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`,
              zIndex: 9999
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Menu Header */}
            <div className="px-3 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700">
              Row Actions
            </div>

            {/* Menu Items */}
            <button
              onClick={handleAction(() => onAddRowAbove(rowIndex))}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Row Above
            </button>

            <button
              onClick={handleAction(() => onAddRowBelow(rowIndex))}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Row Below
            </button>

            <hr className="my-1 border-slate-100 dark:border-slate-700" />

            <button
              onClick={handleAction(() => onToggleSummary(rowIndex))}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors ${
                isSummary
                  ? 'text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/30'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'
              }`}
            >
              <Tag className="w-4 h-4" />
              {isSummary ? 'Unmark Summary' : 'Mark as Summary'}
            </button>

            <hr className="my-1 border-slate-100 dark:border-slate-700" />

            <button
              onClick={handleAction(() => onDeleteRow(rowIndex))}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete Row
            </button>
          </div>,
          document.body
        )
      )}
    </>
  );
});

export default TableRow;

