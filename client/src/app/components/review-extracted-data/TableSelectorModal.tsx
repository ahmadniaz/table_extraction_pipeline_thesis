/**
 * Table Selector Modal Component
 * 
 * Allows users to select which table should be used for AI field mapping
 * when multiple tables are extracted from a document.
 */

"use client";

import React, { useState } from 'react';
import { toast } from 'react-hot-toast';

export interface TableAnalysis {
  table_index: number;
  suitability_score: number;
  reasoning: string;
  recommended_for_mapping: boolean;
  headers: string[];
  row_count: number;
}

interface TableSelectorModalProps {
  show: boolean;
  tables: Array<{
    header?: string[];
    headers?: string[];
    rows: any[][];
    name?: string;
  }>;
  tableAnalysis: TableAnalysis[];
  recommendedIndex: number;
  currentIndex?: number;
  onSelect: (index: number) => void;
  onCancel: () => void;
  loading?: boolean;
}

export default function TableSelectorModal({
  show,
  tables,
  tableAnalysis,
  recommendedIndex,
  currentIndex,
  onSelect,
  onCancel,
  loading = false
}: TableSelectorModalProps) {
  const [selectedIndex, setSelectedIndex] = useState(currentIndex ?? recommendedIndex);

  if (!show) return null;

  const handleSelect = () => {
    if (loading) return;
    onSelect(selectedIndex);
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400';
    if (score >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getScoreBgColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700';
    if (score >= 0.6) return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700';
    return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700';
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={loading ? undefined : onCancel}
      />

      {/* Modal */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Select Table for Field Mapping
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    AI has analyzed {tables.length} tables. Choose the best one for mapping.
                  </p>
                </div>
              </div>
              {!loading && (
                <button
                  onClick={onCancel}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
                  type="button"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
            <div className="space-y-4">
              {tables.map((table, index) => {
                const analysis = tableAnalysis.find(a => a.table_index === index);
                const headers = table.header || table.headers || [];
                const rows = table.rows || [];
                const isSelected = selectedIndex === index;
                const isRecommended = index === recommendedIndex;
                const score = analysis?.suitability_score || 0;

                return (
                  <div
                    key={index}
                    onClick={() => !loading && setSelectedIndex(index)}
                    className={`border-2 rounded-lg p-5 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md'
                        : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {/* Table Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold ${
                          isSelected
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h4 className="font-semibold text-gray-900 dark:text-white">
                              {table.name || `Table ${index + 1}`}
                            </h4>
                            {isRecommended && (
                              <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs font-semibold rounded-full">
                                AI Recommended
                              </span>
                            )}
                            {isSelected && (
                              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs font-semibold rounded-full">
                                Selected
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {rows.length} rows × {headers.length} columns
                          </p>
                        </div>
                      </div>

                      {/* Suitability Score */}
                      {analysis && (
                        <div className={`px-3 py-2 rounded-lg border ${getScoreBgColor(score)}`}>
                          <div className="text-center">
                            <div className={`text-2xl font-bold ${getScoreColor(score)}`}>
                              {Math.round(score * 100)}%
                            </div>
                            <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mt-1">
                              Suitability
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Headers Preview */}
                    <div className="mb-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <svg className="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Headers:</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {headers.slice(0, 5).map((header, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-md"
                          >
                            {header}
                          </span>
                        ))}
                        {headers.length > 5 && (
                          <span className="px-3 py-1 bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-400 text-sm rounded-md">
                            +{headers.length - 5} more
                          </span>
                        )}
                      </div>
                    </div>

                    {/* AI Reasoning */}
                    {analysis && (
                      <div className="bg-white dark:bg-gray-900/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                        <div className="flex items-start space-x-2">
                          <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                              AI Analysis:
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                              {analysis.reasoning}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 dark:bg-gray-900 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Selected: <span className="font-semibold text-gray-900 dark:text-white">Table {selectedIndex + 1}</span>
              </p>
              <div className="flex items-center space-x-3">
                <button
                  onClick={onCancel}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  type="button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSelect}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  type="button"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Use Selected Table</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

