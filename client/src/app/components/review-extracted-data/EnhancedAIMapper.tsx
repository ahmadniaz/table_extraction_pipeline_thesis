/**
 * Enhanced AI Mapper Component
 * 
 * Provides intelligent table selection and switching capabilities for AI field mapping.
 * Allows users to switch between different tables and re-run AI mapping analysis.
 */

"use client";

import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import AIIntelligentMappingDisplay from '../AIIntelligentMappingDisplay';
import TableSelectorModal, { TableAnalysis } from './TableSelectorModal';

interface TableData {
  header?: string[];
  headers?: string[];
  rows: any[][];
  name?: string;
}

interface AIIntelligence {
  enabled: boolean;
  field_mapping: {
    ai_enabled: boolean;
    mappings: any[];
    unmapped_fields: string[];
    confidence: number;
    statistics?: Record<string, any>;
    learned_format_used?: boolean;
    selected_table_index?: number;
  };
  plan_type_detection: {
    ai_enabled: boolean;
    detected_plan_types: any[];
    confidence: number;
    multi_plan_document?: boolean;
    statistics?: Record<string, any>;
  };
  table_selection?: {
    enabled: boolean;
    selected_table_index: number;
    confidence: number;
    requires_user_confirmation?: boolean;
    table_analysis?: TableAnalysis[];
    total_tables?: number;
    user_selected?: boolean;
  };
  overall_confidence: number;
}

interface EnhancedAIMapperProps {
  tables: TableData[];
  currentTableIndex: number;
  aiIntelligence?: AIIntelligence;
  uploadId?: string;
  onTableSwitch?: (newIndex: number) => Promise<void>;
  onMappingUpdate?: (newMappings: any) => void;
  tableHeaders?: string[];
  databaseFields?: Array<{ id: string; display_name: string; description?: string }>;
  acceptedFields?: string[];
  skippedFields?: string[];
  onAcceptMapping?: (mapping: any) => void;
  onRejectMapping?: (mapping: any) => void;
  onSkipMapping?: (mapping: any) => void;
  onAcceptAllMappings?: () => void;
  onReviewMappings?: () => void;
  onCustomMapping?: (extractedField: string, selectedHeader: string, databaseField?: string) => void;
}

export default function EnhancedAIMapper({
  tables,
  currentTableIndex,
  aiIntelligence,
  uploadId,
  onTableSwitch,
  onMappingUpdate,
  tableHeaders,
  databaseFields,
  acceptedFields,
  skippedFields,
  onAcceptMapping,
  onRejectMapping,
  onSkipMapping,
  onAcceptAllMappings,
  onReviewMappings,
  onCustomMapping
}: EnhancedAIMapperProps) {
  const [loading, setLoading] = useState(false);
  const [showTableSelector, setShowTableSelector] = useState(false);
  const [selectedTableIndex, setSelectedTableIndex] = useState(currentTableIndex);

  const handleTableSwitch = async (newIndex: number) => {
    if (loading || newIndex === currentTableIndex) {
      setShowTableSelector(false);
      return;
    }

    setLoading(true);
    setShowTableSelector(false);

    try {
      // Call the table switch API
      if (onTableSwitch) {
        await onTableSwitch(newIndex);
        setSelectedTableIndex(newIndex);
        toast.success(`✅ Switched to Table ${newIndex + 1} and re-ran AI field mapping`);
      } else if (uploadId) {
        // Call API directly if onTableSwitch not provided
        const response = await fetch('/api/ai/switch-mapping-table', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            upload_id: uploadId,
            new_table_index: newIndex,
            reason: 'user_requested'
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to switch table');
        }

        const result = await response.json();
        
        if (result.success && onMappingUpdate) {
          onMappingUpdate(result);
        }

        setSelectedTableIndex(newIndex);
        toast.success(`✅ ${result.message}`);
      }
    } catch (error) {
      console.error('Error switching table:', error);
      toast.error('❌ Failed to switch table. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDropdownSwitch = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newIndex = parseInt(event.target.value);
    await handleTableSwitch(newIndex);
  };

  // Check if multiple tables exist
  const hasMultipleTables = tables && tables.length > 1;
  const tableSelection = aiIntelligence?.table_selection;
  const recommendedIndex = tableSelection?.table_analysis?.[0]?.table_index ?? 0;

  // Show confirmation prompt if AI recommends a different table
  const shouldShowConfirmation = 
    hasMultipleTables && 
    tableSelection?.requires_user_confirmation && 
    !tableSelection?.user_selected;

  return (
    <div className="space-y-4">
      {/* Table Selection Controls */}
      {hasMultipleTables && (
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md border border-gray-200 dark:border-slate-700 p-5">
          {/* First Row - Header and Description */}
          <div className="mb-4">
            <div className="flex items-center space-x-3 mb-2">
              <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h4 className="text-lg font-semibold text-gray-900 dark:text-slate-100">
                Table Selection for Field Mapping
              </h4>
            </div>
            <p className="text-sm text-gray-600 dark:text-slate-400">
              {tableSelection?.user_selected 
                ? 'You selected this table for field mapping'
                : tableSelection?.enabled 
                  ? `AI selected this table with ${Math.round((tableSelection.confidence || 0) * 100)}% confidence`
                  : 'Currently using this table for field mapping'}
            </p>
          </div>

          {/* Second Row - Controls */}
          <div className="flex items-center space-x-3 w-full sm:w-auto">
            {/* Current Table Selector */}
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
              Current Table:
            </label>
            <select
              value={currentTableIndex}
              onChange={handleDropdownSwitch}
              disabled={loading}
              className="flex-1 sm:flex-none px-3 py-2 bg-white dark:bg-slate-700 border-2 border-gray-300 dark:border-slate-600 rounded-lg text-sm font-medium text-gray-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed min-w-[200px]"
            >
              {tables.map((table, index) => {
                const headers = table.header || table.headers || [];
                const rows = table.rows || [];
                return (
                  <option key={index} value={index}>
                    Table {index + 1} - {headers.length} cols, {rows.length} rows
                    {index === recommendedIndex ? ' ⭐ AI Pick' : ''}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Loading Indicator */}
          {loading && (
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
              <div className="flex items-center space-x-3">
                <svg className="animate-spin h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-sm font-medium text-blue-900 dark:text-blue-300">
                  Re-analyzing table and generating new AI field mappings...
                </span>
              </div>
            </div>
          )}

          {/* Confirmation Prompt */}
          {shouldShowConfirmation && !loading && (
            <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-700">
              <div className="flex items-start space-x-3">
                <svg className="w-6 h-6 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-yellow-900 dark:text-yellow-300 mb-2">
                    AI has low confidence in table selection
                  </p>
                  <p className="text-sm text-yellow-800 dark:text-yellow-400">
                    Please review the table selection using the dropdown above to choose the best table for field mapping.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Field Mapping Display */}
      {aiIntelligence && (
        <AIIntelligentMappingDisplay
          aiIntelligence={aiIntelligence}
          tableHeaders={tableHeaders}
          databaseFields={databaseFields}
          acceptedFields={acceptedFields}
          skippedFields={skippedFields}
          onAcceptMapping={onAcceptMapping}
          onRejectMapping={onRejectMapping}
          onSkipMapping={onSkipMapping}
          onAcceptAllMappings={onAcceptAllMappings}
          onReviewMappings={onReviewMappings}
          onCustomMapping={onCustomMapping}
        />
      )}

      {/* Table Selector Modal */}
      {showTableSelector && tableSelection?.table_analysis && (
        <TableSelectorModal
          show={showTableSelector}
          tables={tables}
          tableAnalysis={tableSelection.table_analysis}
          recommendedIndex={recommendedIndex}
          currentIndex={currentTableIndex}
          onSelect={handleTableSwitch}
          onCancel={() => setShowTableSelector(false)}
          loading={loading}
        />
      )}
    </div>
  );
}

