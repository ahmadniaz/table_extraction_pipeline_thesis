/**
 * AI Intelligent Mapping Display Component
 * 
 * This component displays AI-powered field mapping suggestions and plan type detections
 * with confidence scores, reasoning, and interactive controls.
 */

"use client";

import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  FieldMapping,
  PlanTypeDetection,
  formatConfidence,
  getConfidenceBadgeColor,
  getConfidenceColor,
  groupMappingsByConfidence,
  formatPlanTypeSummary
} from '../services/aiIntelligentMappingService';

interface AIIntelligentMappingDisplayProps {
  aiIntelligence?: {
    enabled: boolean;
    field_mapping: {
      ai_enabled: boolean;
      mappings: FieldMapping[];
      unmapped_fields: string[];
      confidence: number;
      statistics?: Record<string, any>;
      learned_format_used?: boolean;
      selected_table_index?: number;
    };
    plan_type_detection: {
      ai_enabled: boolean;
      detected_plan_types: PlanTypeDetection[];
      confidence: number;
      multi_plan_document?: boolean;
      statistics?: Record<string, any>;
    };
    table_selection?: {
      enabled: boolean;
      selected_table_index: number;
      confidence: number;
      total_tables?: number;
      user_selected?: boolean;
    };
    overall_confidence: number;
  };
  tableHeaders?: string[];
  databaseFields?: Array<{ id: string; display_name: string; description?: string }>;
  acceptedFields?: string[];
  skippedFields?: string[];
  onAcceptMapping?: (mapping: FieldMapping) => void;
  onRejectMapping?: (mapping: FieldMapping) => void;
  onSkipMapping?: (mapping: FieldMapping) => void;
  onAcceptAllMappings?: () => void;
  onReviewMappings?: () => void;
  onCustomMapping?: (extractedField: string, selectedHeader: string, databaseField?: string) => void;
}

export default function AIIntelligentMappingDisplay({
  aiIntelligence,
  tableHeaders = [],
  databaseFields = [],
  acceptedFields = [],
  skippedFields = [],
  onAcceptMapping,
  onRejectMapping,
  onSkipMapping,
  onAcceptAllMappings,
  onReviewMappings,
  onCustomMapping
}: AIIntelligentMappingDisplayProps) {
  const [expandedMappings, setExpandedMappings] = useState<Set<string>>(new Set());
  const [expandedPlanTypes, setExpandedPlanTypes] = useState<Set<string>>(new Set());
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null);

  if (!aiIntelligence || !aiIntelligence.enabled) {
    return null;
  }

  const { field_mapping, plan_type_detection, table_selection, overall_confidence } = aiIntelligence;
  
  // Get the selected table index for display
  const selectedTableIndex = table_selection?.selected_table_index ?? field_mapping.selected_table_index ?? 0;
  const totalTables = table_selection?.total_tables ?? 1;
  const hasMultipleTables = totalTables > 1;

  const toggleMappingExpand = (field: string) => {
    const newExpanded = new Set(expandedMappings);
    if (newExpanded.has(field)) {
      newExpanded.delete(field);
    } else {
      newExpanded.add(field);
    }
    setExpandedMappings(newExpanded);
  };

  const togglePlanTypeExpand = (planType: string) => {
    const newExpanded = new Set(expandedPlanTypes);
    if (newExpanded.has(planType)) {
      newExpanded.delete(planType);
    } else {
      newExpanded.add(planType);
    }
    setExpandedPlanTypes(newExpanded);
  };

  const groupedMappings = field_mapping.ai_enabled && field_mapping.mappings
    ? groupMappingsByConfidence(field_mapping.mappings)
    : { high: [], medium: [], low: [] };

  // Sort mappings: non-accepted/non-skipped first, then skipped, then accepted last
  const sortMappingsByAcceptance = (mappings: FieldMapping[]) => {
    return [...mappings].sort((a, b) => {
      const aAccepted = acceptedFields.includes(a.extracted_field);
      const bAccepted = acceptedFields.includes(b.extracted_field);
      const aSkipped = skippedFields.includes(a.extracted_field);
      const bSkipped = skippedFields.includes(b.extracted_field);
      
      // Priority: pending > skipped > accepted
      if (aAccepted && !bAccepted) return 1;
      if (!aAccepted && bAccepted) return -1;
      if (aSkipped && !bSkipped && !aAccepted) return 1;
      if (!aSkipped && bSkipped && !bAccepted) return -1;
      
      // Otherwise maintain original order
      return 0;
    });
  };

  // Apply sorting to each confidence group
  const sortedGroupedMappings = {
    high: sortMappingsByAcceptance(groupedMappings.high),
    medium: sortMappingsByAcceptance(groupedMappings.medium),
    low: sortMappingsByAcceptance(groupedMappings.low)
  };

  return (
    <div className="space-y-4">
      {/* Field Mapping Section - Only show this, header and plan type are shown elsewhere */}
      {field_mapping.ai_enabled && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="text-md font-semibold text-gray-900 dark:text-white">
                    Field Mapping Suggestions
                    {hasMultipleTables && (
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 font-normal">
                        (from Table {selectedTableIndex + 1} of {totalTables})
                      </span>
                    )}
                  </h4>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {field_mapping.mappings.length} fields mapped with {formatConfidence(field_mapping.confidence)} confidence
                    {field_mapping.learned_format_used && (
                      <span className="ml-2 text-blue-600 dark:text-blue-400 font-medium">
                        ✓ Using learned format
                      </span>
                    )}
                    {table_selection?.user_selected && (
                      <span className="ml-2 text-purple-600 dark:text-purple-400 font-medium">
                        ✓ User selected table
                      </span>
                    )}
                  </p>
                </div>
              </div>
              {onAcceptAllMappings && sortedGroupedMappings.high.length > 0 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onAcceptAllMappings();
                    toast.success(`✅ Accepted ${sortedGroupedMappings.high.length} high confidence mappings!`);
                    console.log('✅ Accepted all high confidence mappings:', sortedGroupedMappings.high.length, 'mappings');
                  }}
                  className="px-4 py-2 bg-green-500 dark:bg-green-600 hover:bg-green-600 dark:hover:bg-green-700 active:bg-green-700 dark:active:bg-green-800 text-white text-sm font-medium rounded-md transition-all shadow-sm hover:shadow-md active:scale-95"
                  type="button"
                >
                  <span className="flex items-center space-x-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Accept All High Confidence ({sortedGroupedMappings.high.length})</span>
                  </span>
                </button>
              )}
            </div>
          </div>

          {/* Validation Message */}
          {sortedGroupedMappings.low.length > 0 && (
            <div className="mx-6 mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg animate-fadeIn">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="text-sm text-yellow-800">
                  Please review {sortedGroupedMappings.low.length} field mapping(s) before proceeding. 
                  Fields with low confidence scores need your attention.
                </p>
              </div>
            </div>
          )}

          {/* Scrollable Content Area */}
          <div className="p-6 space-y-6 max-h-[600px] overflow-y-auto custom-scrollbar">
            {/* High Confidence Mappings */}
            {sortedGroupedMappings.high.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center space-x-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>High Confidence ({sortedGroupedMappings.high.length})</span>
                </h5>
                <div className="space-y-2">
                  {sortedGroupedMappings.high.map((mapping) => (
                    <MappingCard
                      key={mapping.extracted_field}
                      mapping={mapping}
                      isExpanded={expandedMappings.has(mapping.extracted_field)}
                      onToggleExpand={() => toggleMappingExpand(mapping.extracted_field)}
                      isAccepted={acceptedFields.includes(mapping.extracted_field)}
                      isSkipped={skippedFields.includes(mapping.extracted_field)}
                      onAccept={onAcceptMapping}
                      onSkip={onSkipMapping}
                      databaseFields={databaseFields}
                      tableHeaders={tableHeaders}
                      onCustomMapping={onCustomMapping}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Medium Confidence Mappings */}
            {sortedGroupedMappings.medium.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center space-x-2">
                  <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                  <span>Medium Confidence ({sortedGroupedMappings.medium.length})</span>
                </h5>
                <div className="space-y-2">
                  {sortedGroupedMappings.medium.map((mapping) => (
                    <MappingCard
                      key={mapping.extracted_field}
                      mapping={mapping}
                      isExpanded={expandedMappings.has(mapping.extracted_field)}
                      onToggleExpand={() => toggleMappingExpand(mapping.extracted_field)}
                      isAccepted={acceptedFields.includes(mapping.extracted_field)}
                      isSkipped={skippedFields.includes(mapping.extracted_field)}
                      onAccept={onAcceptMapping}
                      onSkip={onSkipMapping}
                      databaseFields={databaseFields}
                      tableHeaders={tableHeaders}
                      onCustomMapping={onCustomMapping}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Low Confidence Mappings */}
            {sortedGroupedMappings.low.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center space-x-2">
                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                  <span>Low Confidence - Requires Review ({sortedGroupedMappings.low.length})</span>
                </h5>
                <div className="space-y-2">
                  {sortedGroupedMappings.low.map((mapping) => (
                    <MappingCard
                      key={mapping.extracted_field}
                      mapping={mapping}
                      isExpanded={expandedMappings.has(mapping.extracted_field)}
                      onToggleExpand={() => toggleMappingExpand(mapping.extracted_field)}
                      isAccepted={acceptedFields.includes(mapping.extracted_field)}
                      isSkipped={skippedFields.includes(mapping.extracted_field)}
                      onAccept={onAcceptMapping}
                      onSkip={onSkipMapping}
                      databaseFields={databaseFields}
                      tableHeaders={tableHeaders}
                      onCustomMapping={onCustomMapping}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Unmapped Fields */}
            {field_mapping.unmapped_fields && field_mapping.unmapped_fields.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Unmapped Fields ({field_mapping.unmapped_fields.length})
                </h5>
                <div className="flex flex-wrap gap-2">
                  {field_mapping.unmapped_fields.map((field) => (
                    <span
                      key={field}
                      className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md text-sm"
                    >
                      {field}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Mapping Card Component - Enhanced with better interactivity
function MappingCard({
  mapping,
  isExpanded,
  onToggleExpand,
  isAccepted = false,
  isSkipped = false,
  onAccept,
  onSkip,
  databaseFields,
  tableHeaders,
  onCustomMapping
}: {
  mapping: FieldMapping;
  isExpanded: boolean;
  onToggleExpand: () => void;
  isAccepted?: boolean;
  isSkipped?: boolean;
  onAccept?: (mapping: FieldMapping) => void;
  onSkip?: (mapping: FieldMapping) => void;
  databaseFields?: Array<{ id: string; display_name: string; description?: string }>;
  tableHeaders?: string[];
  onCustomMapping?: (extractedField: string, selectedHeader: string, databaseField?: string) => void;
}) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedDatabaseField, setSelectedDatabaseField] = useState(mapping.mapped_to);
  const [selectedTableHeader, setSelectedTableHeader] = useState(mapping.extracted_field);
  return (
    <div className={`border-2 rounded-xl overflow-hidden transition-all shadow-sm ${
      isAccepted 
        ? 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-800/50 opacity-60'
        : isSkipped
          ? 'border-orange-300 dark:border-orange-600 bg-orange-50 dark:bg-orange-900/10 opacity-70'
          : mapping.requires_review
            ? 'border-red-300 dark:border-red-600 bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 hover:shadow-md'
            : 'border-green-200 dark:border-green-700 bg-white dark:bg-gray-800 hover:shadow-md'
    }`}>
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 flex-wrap gap-y-2">
              <span className="font-mono text-sm font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded-md">
                {mapping.extracted_field}
              </span>
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
              <span className="text-sm font-bold text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-md">
                {mapping.mapped_to}
              </span>
              <span className={`text-xs font-semibold px-3 py-1 rounded-full ${getConfidenceBadgeColor(mapping.confidence)}`}>
                {formatConfidence(mapping.confidence)}
              </span>
              {mapping.requires_review && !isAccepted && (
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-red-200 dark:bg-red-800 text-red-900 dark:text-red-100 border border-red-400 dark:border-red-600">
                  ⚠ Review Required
                </span>
              )}
              {isAccepted && (
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 border border-green-300 dark:border-green-700">
                  ✓ Accepted
                </span>
              )}
              {isSkipped && !isAccepted && (
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-300 dark:border-orange-700">
                  ⊘ Skipped
                </span>
              )}
            </div>
          </div>
          {!isAccepted && !isSkipped && (
            <div className="flex items-center space-x-1 ml-4">
              {/* Accept Button */}
              {onAccept && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onAccept(mapping);
                    toast.success(`✅ Accepted: ${mapping.extracted_field} → ${mapping.mapped_to}`);
                    console.log('✅ Accepted mapping:', mapping.extracted_field, '→', mapping.mapped_to);
                  }}
                  className="p-2.5 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-lg transition-all hover:scale-110 active:scale-95"
                  title="Accept mapping"
                  type="button"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </button>
              )}
              
              {/* Dropdown Button for Custom Mapping */}
              {onCustomMapping && tableHeaders && tableHeaders.length > 0 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDropdown(!showDropdown);
                  }}
                  className="p-2.5 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-all"
                  title="Change mapping"
                  type="button"
                >
                  <svg className={`w-5 h-5 transform transition-transform duration-200 ${showDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}

              {/* Skip Button */}
              {onSkip && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSkip(mapping);
                    toast.success(`⊘ Skipped: ${mapping.extracted_field}`);
                    console.log('⊘ Skipped mapping:', mapping.extracted_field);
                  }}
                  className="p-2.5 text-orange-600 hover:bg-orange-100 dark:hover:bg-orange-900/30 rounded-lg transition-all hover:scale-110 active:scale-95"
                  title="Skip this field"
                  type="button"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Expanded Dropdown Section */}
        {showDropdown && !isAccepted && !isSkipped && onCustomMapping && (
          <div className="mt-4 pt-4 border-t-2 border-blue-100 dark:border-blue-800 animate-in">
            <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase block mb-2">
                    Database Field:
                  </label>
                  {databaseFields && databaseFields.length > 0 ? (
                    <select
                      value={selectedDatabaseField}
                      onChange={(e) => setSelectedDatabaseField(e.target.value)}
                      className="w-full px-4 py-2.5 bg-white dark:bg-gray-800 border-2 border-blue-200 dark:border-blue-700 rounded-lg text-sm font-medium text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    >
                      {databaseFields.map((field) => (
                        <option key={field.id} value={field.display_name}>
                          {field.display_name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-sm font-bold text-gray-900 dark:text-white bg-white dark:bg-gray-700 px-4 py-2.5 rounded-md border-2 border-gray-200 dark:border-gray-600">
                      {selectedDatabaseField}
                    </div>
                  )}
                </div>
                
                <div>
                  <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase block mb-2">
                    Field to map:
                  </label>
                  {tableHeaders && tableHeaders.length > 0 ? (
                    <select
                      value={selectedTableHeader}
                      onChange={(e) => setSelectedTableHeader(e.target.value)}
                      className="w-full px-4 py-2.5 bg-white dark:bg-gray-800 border-2 border-blue-200 dark:border-blue-700 rounded-lg text-sm font-medium text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    >
                      {tableHeaders.map((header, idx) => (
                        <option key={idx} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-sm font-bold text-gray-900 dark:text-white bg-white dark:bg-gray-700 px-4 py-2.5 rounded-md border-2 border-gray-200 dark:border-gray-600">
                      {selectedTableHeader}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => {
                    if (onCustomMapping) {
                      onCustomMapping(selectedTableHeader, selectedTableHeader, selectedDatabaseField);
                      toast.success(`✅ Mapped ${selectedTableHeader} → ${selectedDatabaseField}`);
                      setShowDropdown(false);
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-800 text-white rounded-lg font-medium transition-all shadow-sm hover:shadow-md"
                  type="button"
                >
                  Apply Mapping
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mt-5 pt-5 border-t-2 border-blue-100 dark:border-blue-800 space-y-4 animate-in">
            <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
              <h6 className="text-xs font-bold text-blue-900 dark:text-blue-300 mb-2 uppercase tracking-wide">AI Reasoning:</h6>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{mapping.reasoning}</p>
            </div>
            {mapping.alternatives && mapping.alternatives.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-900/60 rounded-lg p-4">
                <h6 className="text-xs font-bold text-gray-900 dark:text-gray-300 mb-3 uppercase tracking-wide flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12M8 12h12m-12 5h12" />
                  </svg>
                  Alternative Mappings:
                </h6>
                <div className="space-y-2">
                  {mapping.alternatives.map((alt, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-all">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{alt.field}</span>
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${getConfidenceBadgeColor(alt.confidence)}`}>
                        {formatConfidence(alt.confidence)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Plan Type Card Component - Enhanced with better interactivity
function PlanTypeCard({
  detection,
  isExpanded,
  onToggleExpand
}: {
  detection: PlanTypeDetection;
  isExpanded: boolean;
  onToggleExpand: () => void;
}) {
  return (
    <div className={`border-2 rounded-xl overflow-hidden transition-all shadow-sm hover:shadow-md ${
      detection.requires_review
        ? 'border-yellow-300 dark:border-yellow-700 bg-gradient-to-br from-yellow-50 to-yellow-100 dark:bg-yellow-900/10'
        : 'border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-800'
    }`}>
      <div className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="text-lg font-bold text-gray-900 dark:text-white">
                {detection.plan_type}
              </span>
              <span className={`text-xs font-semibold px-3 py-1 rounded-full ${getConfidenceBadgeColor(detection.confidence)}`}>
                {formatConfidence(detection.confidence)}
              </span>
              {detection.requires_review && (
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-yellow-200 text-yellow-900 border border-yellow-400">
                  ⚠ Requires Review
                </span>
              )}
            </div>
            {!isExpanded && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 ml-11">
                {detection.reasoning}
              </p>
            )}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            className="p-2.5 text-purple-600 hover:bg-purple-100 dark:hover:bg-purple-900 rounded-lg transition-all ml-4 hover:shadow-sm active:scale-95"
            title={isExpanded ? "Collapse details" : "Expand details"}
            type="button"
          >
            <svg className={`w-5 h-5 transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mt-5 pt-5 border-t-2 border-purple-100 dark:border-purple-800 space-y-4 animate-in">
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
              <h6 className="text-xs font-bold text-purple-900 dark:text-purple-300 mb-2 uppercase tracking-wide">AI Reasoning:</h6>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{detection.reasoning}</p>
            </div>
            {detection.evidence && detection.evidence.length > 0 && (
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <h6 className="text-xs font-bold text-green-900 dark:text-green-300 mb-3 uppercase tracking-wide flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Supporting Evidence:
                </h6>
                <ul className="space-y-2">
                  {detection.evidence.map((evidence, idx) => (
                    <li key={idx} className="text-sm text-gray-700 dark:text-gray-300 flex items-start">
                      <span className="text-green-600 dark:text-green-400 mr-2 font-bold">✓</span>
                      <span className="flex-1">{evidence}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

