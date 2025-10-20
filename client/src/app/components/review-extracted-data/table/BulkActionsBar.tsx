/**
 * Bulk Actions Bar Component
 * Appears when rows are selected, provides bulk operations
 */

'use client';

import React from 'react';
import { Trash2, X, Tag } from 'lucide-react';

interface BulkActionsBarProps {
  selectedCount: number;
  onDeleteSelected: () => void;
  onMarkAsSummary: () => void;
  onClearSelection: () => void;
}

export default function BulkActionsBar({
  selectedCount,
  onDeleteSelected,
  onMarkAsSummary,
  onClearSelection
}: BulkActionsBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-20 left-0 right-0 bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-800 dark:to-purple-800 text-white px-6 py-4 shadow-2xl z-30 animate-slide-up">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white/20 dark:bg-white/30 rounded-full flex items-center justify-center">
              <span className="text-sm font-bold">{selectedCount}</span>
            </div>
            <span className="font-medium">
              {selectedCount} row{selectedCount !== 1 ? 's' : ''} selected
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onMarkAsSummary}
            className="flex items-center gap-2 px-4 py-2 bg-orange-500 dark:bg-orange-600 hover:bg-orange-600 dark:hover:bg-orange-700 rounded-lg font-medium transition-all hover:scale-105 active:scale-95"
            title="Mark selected rows as summary rows"
          >
            <Tag className="w-4 h-4" />
            Mark as Summary
          </button>
          
          <button
            onClick={onDeleteSelected}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 dark:bg-red-600 hover:bg-red-600 dark:hover:bg-red-700 rounded-lg font-medium transition-all hover:scale-105 active:scale-95"
            title="Delete selected rows"
          >
            <Trash2 className="w-4 h-4" />
            Delete Selected
          </button>

          <button
            onClick={onClearSelection}
            className="flex items-center gap-2 px-4 py-2 bg-gray-500 dark:bg-gray-600 hover:bg-gray-600 dark:hover:bg-gray-700 rounded-lg font-medium transition-all hover:scale-105 active:scale-95"
            title="Clear selection"
          >
            <X className="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}

