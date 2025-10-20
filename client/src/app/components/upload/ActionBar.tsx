/**
 * Modern Action Bar Component
 * 
 * Context-sensitive action bar with progress stats, validation messages,
 * and smooth transitions between modes.
 */

"use client";

import React from 'react';
import { ArrowRight, ArrowLeft, Check } from 'lucide-react';

export interface MappingStats {
  mapped: number;
  needsReview: number;
  unmapped: number;
  total: number;
}

export type ViewMode = 'table_review' | 'field_mapping' | 'plan_selection';

interface ActionBarProps {
  viewMode: ViewMode;
  mappingStats?: MappingStats;
  onModeChange: (mode: ViewMode) => void | Promise<void>;
  onFinalSubmit: () => Promise<void>;
  isSubmitting?: boolean;
  canProceed?: boolean;
  isTransitioning?: boolean;
  carrierName?: string;
  statementDate?: string;
}

export default function ActionBar({
  viewMode,
  mappingStats,
  onModeChange,
  onFinalSubmit,
  isSubmitting = false,
  canProceed = true,
  isTransitioning = false,
  carrierName = '',
  statementDate = ''
}: ActionBarProps) {
  const handleSubmit = async () => {
    if (!isSubmitting && canProceed) {
      await onFinalSubmit();
    }
  };

  const handleModeChange = async (mode: ViewMode) => {
    if (!isTransitioning) {
      await onModeChange(mode);
    }
  };

  const hasReviewRequired = mappingStats && mappingStats.needsReview > 0;
  const canSubmit = !hasReviewRequired && canProceed && !isSubmitting;
  
  // Validation for table review mode
  const isCarrierNameMissing = !carrierName || carrierName.trim() === '' || carrierName === 'Unknown';
  const isStatementDateMissing = !statementDate || statementDate.trim() === '' || statementDate === 'Not detected';
  const canContinueToMapping = !isCarrierNameMissing && !isStatementDateMissing;
  
  // Generate validation message
  const getValidationMessage = () => {
    if (isCarrierNameMissing && isStatementDateMissing) {
      return 'Please provide both Carrier Name and Statement Date';
    } else if (isCarrierNameMissing) {
      return 'Please provide Carrier Name';
    } else if (isStatementDateMissing) {
      return 'Please provide Statement Date';
    }
    return '';
  };

  return (
    <div className="sticky bottom-0 bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 px-6 py-4 shadow-lg">
      <div className="flex items-center justify-between">
        
        {/* Progress Stats - Only show in field mapping mode */}
        {viewMode === 'field_mapping' && mappingStats && (
          <div className="flex flex-col space-y-2">
            <div className="flex items-center space-x-6 text-sm">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                <span className="text-gray-700 dark:text-slate-300">
                  <span className="font-semibold text-green-600 dark:text-green-400">{mappingStats.mapped}</span> mapped
                </span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                <span className="text-gray-700 dark:text-slate-300">
                  <span className="font-semibold text-yellow-600 dark:text-yellow-400">{mappingStats.needsReview}</span> need review
                </span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-gray-400 rounded-full mr-2"></div>
                <span className="text-gray-700 dark:text-slate-300">
                  <span className="font-semibold text-gray-600 dark:text-slate-400">{mappingStats.unmapped}</span> unmapped
                </span>
              </div>
            </div>
            {/* Helpful message when fields need review */}
            {hasReviewRequired && (
              <p className="text-xs text-yellow-700 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 rounded px-3 py-1.5 inline-block">
                ⚠️ Please accept or manually map all fields marked for review before submitting
              </p>
            )}
          </div>
        )}

        {/* Table Review Mode Stats */}
        {viewMode === 'table_review' && (
          <div className="flex flex-col space-y-2">
            <div className="text-sm text-gray-600 dark:text-slate-400">
              Review your extracted data and make any necessary corrections before proceeding to field mapping.
            </div>
            {!canContinueToMapping && (
              <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded px-3 py-2 inline-block">
                ⚠️ {getValidationMessage()}. Click the <span className="font-semibold">✏️ Edit</span> button above to add missing information.
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center space-x-4">
          
          {viewMode === 'table_review' ? (
            // Table Review Mode - Single Continue Button with validation
            <div className="relative group">
              <button
                onClick={() => canContinueToMapping && handleModeChange('field_mapping')}
                disabled={isTransitioning || !canContinueToMapping}
                className={`px-8 py-3 rounded-lg font-medium transition-colors flex items-center shadow-sm ${
                  isTransitioning || !canContinueToMapping
                    ? 'bg-gray-400 dark:bg-slate-600 text-gray-200 dark:text-slate-400 cursor-not-allowed'
                    : 'bg-blue-600 dark:bg-blue-700 text-white hover:bg-blue-700 dark:hover:bg-blue-600'
                }`}
              >
                {isTransitioning ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Transitioning...
                  </>
                ) : (
                  <>
                    Continue to Field Mapping
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </button>
              {/* Tooltip on hover when disabled */}
              {!canContinueToMapping && !isTransitioning && (
                <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 hidden group-hover:block z-50">
                  <div className="bg-gray-900 dark:bg-slate-700 text-white text-sm rounded-lg px-4 py-2 whitespace-nowrap shadow-lg">
                    {getValidationMessage()}
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                      <div className="border-8 border-transparent border-t-gray-900 dark:border-t-slate-700"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Field Mapping Mode - Back and Submit Buttons
            <div className="flex space-x-3">
              <button
                onClick={() => handleModeChange('table_review')}
                disabled={isTransitioning}
                className={`px-6 py-3 border border-gray-300 dark:border-slate-600 rounded-lg font-medium transition-colors flex items-center ${
                  isTransitioning
                    ? 'bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500 cursor-not-allowed'
                    : 'text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700'
                }`}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Review
              </button>
              
              <button
                onClick={handleSubmit}
                disabled={!canSubmit}
                className={`
                  px-8 py-3 rounded-lg font-medium flex items-center transition-colors shadow-sm
                  ${!canSubmit 
                    ? 'bg-gray-300 dark:bg-slate-600 text-gray-500 dark:text-slate-400 cursor-not-allowed'
                    : 'bg-green-600 dark:bg-green-700 text-white hover:bg-green-700 dark:hover:bg-green-600'}
                `}
              >
                {isSubmitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Processing...
                  </>
                ) : (
                  <>
                    Save & Approve
                    <Check className="w-5 h-5 ml-2" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Progress indicator component for table review mode
export function TableReviewProgress({ currentTable, totalTables }: { currentTable: number; totalTables: number }) {
  const progress = totalTables > 0 ? (currentTable / totalTables) * 100 : 0;

  return (
    <div className="flex items-center space-x-3">
      <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className="bg-blue-600 dark:bg-blue-500 h-full transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <span className="text-sm text-gray-600 dark:text-gray-400 font-medium whitespace-nowrap">
        Table {currentTable} of {totalTables}
      </span>
    </div>
  );
}

