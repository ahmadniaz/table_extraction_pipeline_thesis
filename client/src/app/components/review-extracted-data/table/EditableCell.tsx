/**
 * Editable Cell Component
 * Inline editable table cell with click-to-edit functionality
 */

'use client';

import React, { memo, useCallback, useRef, useEffect, useMemo } from 'react';

interface EditableCellProps {
  value: string;
  isEditing: boolean;
  onStartEdit: () => void;
  onSave: (value: string) => void;
  onCancel: () => void;
  className?: string;
}

const EditableCell = memo(function EditableCell({
  value,
  isEditing,
  onStartEdit,
  onSave,
  onCancel,
  className = ''
}: EditableCellProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [editValue, setEditValue] = React.useState(value);
  
  // Compute display value with professional em dash for empty cells
  const displayValue = useMemo(() => {
    if (!value || value.toString().trim() === '' || value === 'Empty') {
      return '—'; // Em dash for professional appearance
    }
    return value;
  }, [value]);

  // Focus input when editing starts and adjust height
  useEffect(() => {
    if (isEditing && inputRef.current) {
      const textarea = inputRef.current;
      textarea.focus();
      textarea.select();
      // Adjust height to content, but keep minimum height
      textarea.style.height = 'auto';
      const newHeight = textarea.scrollHeight;
      if (newHeight > 24) {
        textarea.style.height = newHeight + 'px';
      } else {
        textarea.style.height = '24px';
      }
    }
  }, [isEditing]);

  // Update edit value when value prop changes
  useEffect(() => {
    if (!isEditing) {
      setEditValue(value);
    }
  }, [value, isEditing]);

  const handleSave = useCallback(() => {
    onSave(editValue);
  }, [editValue, onSave]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  }, [handleSave, onCancel]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditValue(e.target.value);
    // Auto-resize based on content
    const textarea = e.target;
    textarea.style.height = 'auto';
    // Only expand if content actually needs more space
    const newHeight = textarea.scrollHeight;
    if (newHeight > 24) { // Only expand if content is taller than min-height
      textarea.style.height = newHeight + 'px';
    } else {
      textarea.style.height = '24px'; // Keep at minimum height for single line
    }
  }, []);

  if (isEditing) {
    return (
      <textarea
        ref={inputRef}
        value={editValue}
        onChange={handleChange}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className={`w-full focus:outline-none bg-white dark:bg-slate-800 resize-none overflow-hidden text-gray-900 dark:text-slate-300 min-h-[24px] ${className}`}
        style={{
          resize: 'none'
        }}
        rows={1}
      />
    );
  }

  return (
    <div
      onClick={onStartEdit}
      className={`cursor-pointer transition-colors min-h-[24px] flex items-center ${className}`}
      title={value || 'Empty cell'}
    >
      <span className={displayValue === '—' ? 'text-gray-400 dark:text-slate-500' : ''}>
        {displayValue}
      </span>
    </div>
  );
});

export default EditableCell;

