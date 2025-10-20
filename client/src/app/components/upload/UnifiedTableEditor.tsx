/**
 * Unified Table Editor Component
 * 
 * Two-phase layout with smooth transitions:
 * - Phase 1 (table_review): Left = PDF Preview, Right = Editable Table
 * - Phase 2 (field_mapping): Left = Compact Table, Right = AI Field Mapping
 */

"use client";

import React, { useState, useMemo } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { FieldMapping, PlanTypeDetection, getEnhancedExtractionAnalysis } from '@/app/services/aiIntelligentMappingService';
import { useTheme } from '@/context/ThemeContext';
import ActionBar, { MappingStats, ViewMode } from './ActionBar';
import EnhancedAIMapper from '../review-extracted-data/EnhancedAIMapper';
import { ExtractedDataTable } from '../review-extracted-data';
import PDFViewer from './PDFViewer';
import '../review-extracted-data/styles.css';
import PremiumProgressLoader, { UploadStep } from './PremiumProgressLoader';
import { ArrowRight, Map, FileText, Table2, Moon, Sun } from 'lucide-react';

export interface ExtractedData {
  tables: any[];
  planType?: string;
  planTypeConfidence?: number;
  carrierName?: string;
  statementDate?: string;
  gcs_url?: string;
  file_name?: string;
  extracted_carrier?: string;
  extracted_date?: string;
  upload_id?: string;
  company_id?: string;
  carrier_id?: string;
  document_metadata?: {
    carrier_name?: string;
    carrier_confidence?: number;
    statement_date?: string;
    date_confidence?: number;
    broker_company?: string;
    document_type?: string;
  };
  ai_intelligence?: {
    enabled: boolean;
    field_mapping: {
      ai_enabled: boolean;
      mappings: FieldMapping[];
      unmapped_fields: string[];
      confidence: number;
      statistics?: any;
      learned_format_used?: boolean;
    };
    plan_type_detection: {
      ai_enabled: boolean;
      detected_plan_types: PlanTypeDetection[];
      confidence: number;
      multi_plan_document?: boolean;
      statistics?: any;
    };
    overall_confidence: number;
  };
}

interface UnifiedTableEditorProps {
  extractedData: ExtractedData;
  uploadData?: any;
  databaseFields: Array<{ id: string; display_name: string; description?: string }>;
  onDataUpdate: (data: any) => void;
  onSubmit: (finalData: any) => Promise<void>;
  selectedStatementDate?: any;
}

export default function UnifiedTableEditor({
  extractedData,
  uploadData,
  databaseFields,
  onDataUpdate,
  onSubmit,
  selectedStatementDate
}: UnifiedTableEditorProps) {
  const { theme, setTheme, actualTheme } = useTheme();
  const [viewMode, setViewMode] = useState<ViewMode>('table_review');
  const [userMappings, setUserMappings] = useState<Record<string, string>>({});
  const [acceptedMappings, setAcceptedMappings] = useState<Array<{field: string, mapsTo: string, confidence: number, sample: string}>>([]);
  const [skippedFields, setSkippedFields] = useState<Array<{field: string, mapsTo: string, confidence: number, sample: string}>>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Normalize tables: ensure summaryRows is a Set
  const [tables, setTables] = useState(() => {
    const initialTables = extractedData.tables || [];
    return initialTables.map(table => ({
      ...table,
      summaryRows: table.summaryRows instanceof Set 
        ? table.summaryRows 
        : new Set(Array.isArray(table.summaryRows) ? table.summaryRows : [])
    }));
  });
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [newlyAddedField, setNewlyAddedField] = useState<string | null>(null);
  const [approvalStep, setApprovalStep] = useState(0);
  const [approvalProgress, setApprovalProgress] = useState(0);
  const [isPreviewCollapsed, setIsPreviewCollapsed] = useState(false);
  const [isExtractingWithGPT, setIsExtractingWithGPT] = useState(false);
  const [currentTableIdx, setCurrentTableIdx] = useState(0);
  const [showSummaryRows, setShowSummaryRows] = useState(true);
  const [isLoadingAIMapping, setIsLoadingAIMapping] = useState(false);
  const [aiMappingStep, setAiMappingStep] = useState(0);
  const [aiMappingProgress, setAiMappingProgress] = useState(0);
  const [aiIntelligence, setAiIntelligence] = useState(extractedData.ai_intelligence);
  
  // ===== EDITABLE METADATA STATE =====
  const [editedCarrierName, setEditedCarrierName] = useState(
    extractedData?.carrierName || extractedData?.extracted_carrier || ''
  );
  const [editedPlanType, setEditedPlanType] = useState(
    extractedData?.ai_intelligence?.plan_type_detection?.detected_plan_types?.[0]?.plan_type || ''
  );
  const [editedStatementDate, setEditedStatementDate] = useState(
    extractedData?.statementDate || extractedData?.extracted_date || ''
  );
  const [isEditingMetadata, setIsEditingMetadata] = useState(false);

  // Get AI mappings from state (updated after "Continue to Field Mapping" is clicked)
  const aiMappings = aiIntelligence?.field_mapping?.mappings || [];

  // Auto-accept high-confidence learned format mappings
  React.useEffect(() => {
    const fieldMapping = aiIntelligence?.field_mapping;
    
    // Only auto-accept if:
    // 1. AI field mapping is enabled
    // 2. A learned format was used
    // 3. Overall confidence is >= 0.85
    // 4. acceptedMappings is still empty (first load)
    if (
      fieldMapping?.ai_enabled &&
      fieldMapping?.learned_format_used &&
      fieldMapping?.confidence >= 0.85 &&
      acceptedMappings.length === 0
    ) {
      const tableHeaders = tables?.[0]?.header || tables?.[0]?.headers || [];
      
      // Auto-accept all high-confidence mappings from learned format
      const autoAcceptedMappings = aiMappings
        .filter(mapping => mapping.confidence >= 0.85)
        .map(mapping => {
          const colIndex = tableHeaders.findIndex((h: string) => 
            h.toLowerCase() === mapping.extracted_field.toLowerCase()
          );
          const sampleData = colIndex >= 0 && tables?.[0]?.rows?.[0] 
            ? tables[0].rows[0][colIndex] 
            : 'N/A';

          return {
            field: mapping.extracted_field,
            mapsTo: mapping.mapped_to,
            confidence: mapping.confidence,
            sample: sampleData
          };
        });

      if (autoAcceptedMappings.length > 0) {
        setAcceptedMappings(autoAcceptedMappings);
        
        // Also populate user mappings
        const mappingsUpdate: Record<string, string> = {};
        autoAcceptedMappings.forEach(mapping => {
          mappingsUpdate[mapping.field] = mapping.mapsTo;
        });
        setUserMappings(mappingsUpdate);
        
        // Show success toast
        toast.success(`Auto-accepted ${autoAcceptedMappings.length} field mappings from learned format!`, {
          duration: 3000,
          icon: '✨'
        });
      }
    }
  }, [aiIntelligence, aiMappings, tables]);

  // Define approval process steps
  const APPROVAL_STEPS: UploadStep[] = [
    {
      id: 'saving_tables',
      order: 1,
      title: 'Saving Table Data',
      description: 'Storing your edited table data...',
      estimatedDuration: 2000
    },
    {
      id: 'learning_format',
      order: 2,
      title: 'Learning Format',
      description: 'Learning format patterns for future uploads...',
      estimatedDuration: 1500
    },
    {
      id: 'saving_mappings',
      order: 3,
      title: 'Saving Field Mappings',
      description: 'Storing your field mapping configuration...',
      estimatedDuration: 1500
    },
    {
      id: 'processing_commission',
      order: 4,
      title: 'Processing Commission Data',
      description: 'Calculating commission amounts...',
      estimatedDuration: 3000
    },
    {
      id: 'finalizing',
      order: 5,
      title: 'Finalizing',
      description: 'Completing the approval process...',
      estimatedDuration: 1000
    }
  ];
  
  // Define AI Field Mapping steps
  const AI_MAPPING_STEPS: UploadStep[] = [
    {
      id: 'analyzing_table',
      order: 1,
      title: 'Analyzing Table Structure',
      description: 'Understanding your edited table data...',
      estimatedDuration: 1000
    },
    {
      id: 'checking_learned_formats',
      order: 2,
      title: 'Checking Learned Formats',
      description: 'Looking for previously saved mappings...',
      estimatedDuration: 1500
    },
    {
      id: 'generating_mappings',
      order: 3,
      title: 'AI Field Mapping',
      description: 'Generating intelligent field suggestions...',
      estimatedDuration: 3000
    },
    {
      id: 'finalizing_mappings',
      order: 4,
      title: 'Finalizing',
      description: 'Preparing field mapping suggestions...',
      estimatedDuration: 500
    }
  ];
  
  
  // Calculate mapping statistics
  const mappingStats: MappingStats = useMemo(() => {
    const allMappings = [...aiMappings];
    const total = allMappings.length;
    
    // Get list of accepted field names (check case-insensitively)
    const acceptedFieldNames = new Set(
      acceptedMappings.map(m => m.field.toLowerCase())
    );
    const userMappedFieldNames = new Set(
      Object.keys(userMappings).map(k => k.toLowerCase())
    );
    // Get list of skipped field names (check case-insensitively)
    const skippedFieldNames = new Set(
      skippedFields.map(m => m.field.toLowerCase())
    );
    
    // Count mappings by status, considering user acceptances and skipped fields
    let mapped = 0;
    let needsReview = 0;
    let unmapped = 0;
    
    allMappings.forEach(mapping => {
      const fieldNameLower = mapping.extracted_field.toLowerCase();
      const isAccepted = acceptedFieldNames.has(fieldNameLower) || 
                        userMappedFieldNames.has(fieldNameLower);
      const isSkipped = skippedFieldNames.has(fieldNameLower);
      
      // Skip counting skipped fields in the statistics
      if (isSkipped) {
        return;
      }
      
      if (isAccepted || mapping.confidence >= 0.8) {
        mapped++;
      } else if (mapping.confidence >= 0.6) {
        needsReview++;
      } else {
        unmapped++;
      }
    });

    

    return { mapped, needsReview, unmapped, total };
  }, [aiMappings, userMappings, acceptedMappings, skippedFields]);

  const handleModeTransition = async (newMode: ViewMode) => {
    if (isTransitioning) return;
    
    // ===== CRITICAL: TRIGGER AI FIELD MAPPING WHEN TRANSITIONING TO FIELD_MAPPING MODE =====
    if (newMode === 'field_mapping') {
      try {
        // Set loading state FIRST before transitioning
        setIsLoadingAIMapping(true);
        setAiMappingStep(0);
        setAiMappingProgress(0);
        
        // Then start transition
        setIsTransitioning(true);
        
        // Small delay for exit animation
        await new Promise(resolve => setTimeout(resolve, 150));
        
        // Change view mode
        setViewMode(newMode);
        
        // Small delay to let the UI render
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Now the loader should be visible
        toast.loading('Generating AI field mappings for edited table...', { id: 'ai-mapping' });
        
        // STEP 1: Analyzing Table Structure
        setAiMappingStep(0);
        setAiMappingProgress(10);
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Get the edited table data from current table
        const currentTable = tables[currentTableIdx];
        const headers = currentTable?.header || currentTable?.headers || [];
        const rows = currentTable?.rows || [];
        
        // Prepare data for AI field mapping API (use edited values if available)
        // CRITICAL FIX: Ensure we pass a valid UUID for carrier_id, not "auto-detected"
        let carrier_id = extractedData?.carrier_id || extractedData?.company_id;
        
        // Validate that carrier_id is a valid UUID, not a placeholder string
        if (carrier_id && (carrier_id === 'auto-detected' || carrier_id === 'undefined' || carrier_id === 'null')) {
          console.warn('⚠️ Invalid carrier_id detected:', carrier_id, '- setting to undefined');
          carrier_id = undefined;
        }
        
        const extracted_carrier = editedCarrierName || extractedData?.carrierName || extractedData?.extracted_carrier;
        const statement_date = editedStatementDate || extractedData?.statementDate || extractedData?.extracted_date;
        
        console.log('🤖 Triggering AI field mapping with edited table data:', {
          headers_count: headers.length,
          rows_count: rows.length,
          carrier_id: carrier_id || 'NOT SET',
          carrier_id_type: typeof carrier_id,
          extracted_carrier,
          extractedData_carrier_id: extractedData?.carrier_id,
          extractedData_company_id: extractedData?.company_id
        });
        
        // STEP 2: Checking Learned Formats
        setAiMappingStep(1);
        setAiMappingProgress(30);
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // STEP 3: Generating AI Mappings
        setAiMappingStep(2);
        setAiMappingProgress(50);
        
        // Call AI field mapping API with edited table data
        const aiAnalysis = await getEnhancedExtractionAnalysis(
          headers,
          rows.slice(0, 5), // First 5 rows as sample
          {
            carrier_name: extracted_carrier,
            statement_date: statement_date,
            document_type: 'commission_statement'
          },
          carrier_id,
          extracted_carrier
        );
        
        // STEP 4: Finalizing
        setAiMappingStep(3);
        setAiMappingProgress(90);
        
        // Update AI intelligence state with new field mappings
        // KEEP plan type detection from extraction, only update field mapping
        const newAiIntelligence = {
          enabled: true,
          field_mapping: {
            ai_enabled: aiAnalysis.field_mapping?.success || false,
            mappings: aiAnalysis.field_mapping?.mappings || [],
            unmapped_fields: aiAnalysis.field_mapping?.unmapped_fields || [],
            confidence: aiAnalysis.field_mapping?.confidence || 0.0,
            statistics: {},
            learned_format_used: aiAnalysis.field_mapping?.learned_format_used || false
          },
          // PRESERVE plan type detection from extraction (don't overwrite)
          plan_type_detection: extractedData.ai_intelligence?.plan_type_detection || {
            ai_enabled: aiAnalysis.plan_type_detection?.success || false,
            detected_plan_types: aiAnalysis.plan_type_detection?.detected_plan_types || [],
            confidence: aiAnalysis.plan_type_detection?.confidence || 0.0,
            multi_plan_document: aiAnalysis.plan_type_detection?.multi_plan_document || false,
            statistics: {}
          },
          overall_confidence: aiAnalysis.overall_confidence || 0.0
        };
        
        setAiIntelligence(newAiIntelligence);
        
        // Update extractedData in parent component
        onDataUpdate({
          ...extractedData,
          ai_intelligence: newAiIntelligence
        });
        
        setAiMappingProgress(100);
        
        toast.success(`AI generated ${aiAnalysis.field_mapping?.mappings?.length || 0} field mappings!`, { 
          id: 'ai-mapping',
          duration: 3000
        });
        
        console.log('✅ AI field mapping completed:', {
          mappings_count: aiAnalysis.field_mapping?.mappings?.length || 0,
          confidence: aiAnalysis.field_mapping?.confidence,
          plan_types_count: aiAnalysis.plan_type_detection?.detected_plan_types?.length || 0
        });
        
      } catch (error: any) {
        console.error('❌ AI field mapping failed:', error);
        
        // Check if it's an authentication error
        if (error.message?.includes('401') || error.message?.toLowerCase().includes('unauthorized')) {
          toast.error('⚠️ Session expired. Please refresh the page and try again.', { 
            id: 'ai-mapping',
            duration: 7000
          });
          // Give user time to see the message before potentially redirecting
          setTimeout(() => {
            if (window.location.pathname !== '/auth') {
              window.location.href = '/auth';
            }
          }, 3000);
        } else {
          toast.error('Failed to generate AI field mappings. You can still manually map fields.', { 
            id: 'ai-mapping',
            duration: 5000
          });
        }
        
        // Continue with empty AI intelligence
        setAiIntelligence({
          enabled: false,
          field_mapping: { ai_enabled: false, mappings: [], unmapped_fields: [], confidence: 0.0 },
          plan_type_detection: { ai_enabled: false, detected_plan_types: [], confidence: 0.0, multi_plan_document: false },
          overall_confidence: 0.0
        });
      } finally {
        setIsLoadingAIMapping(false);
        setAiMappingProgress(0);
        setAiMappingStep(0);
        setIsTransitioning(false);
      }
      
      // Reset preview collapse state
      setIsPreviewCollapsed(false);
    } else {
      // Other mode transitions - just do the visual transition
      setIsTransitioning(true);
      
      // Small delay for exit animation
      await new Promise(resolve => setTimeout(resolve, 150));
      
      setViewMode(newMode);
      
      // Complete transition
      await new Promise(resolve => setTimeout(resolve, 100));
      setIsTransitioning(false);
    }
  };

  const handleFinalSubmission = async () => {
    setIsSubmitting(true);
    setApprovalStep(0);
    setApprovalProgress(0);

    try {
      // Debug logging to see what data we have
      
      const upload_id = uploadData?.upload_id || uploadData?.id || extractedData?.upload_id;
      const company_id = uploadData?.company_id || extractedData?.company_id;
      const carrier_id = extractedData?.carrier_id || uploadData?.carrier_id;
      
      
      if (!upload_id) {
        throw new Error('Upload ID is missing');
      }
      
      if (!carrier_id && !company_id) {
        throw new Error('Company ID or Carrier ID is required. Please check the extraction response.');
      }

      // Use the provided selectedStatementDate or parse from extractedData
      console.log('🔍 Statement Date Debug - selectedStatementDate prop:', selectedStatementDate);
      console.log('🔍 Statement Date Debug - extractedData.statementDate:', extractedData?.statementDate);
      console.log('🔍 Statement Date Debug - extractedData.extracted_date:', extractedData?.extracted_date);
      
      let statementDateObj = selectedStatementDate;
      
      // If not provided as prop, try to parse from extractedData
      if (!statementDateObj) {
        console.log('⚠️ No selectedStatementDate prop provided, parsing from extractedData...');
        const statementDateStr = extractedData?.statementDate || extractedData?.extracted_date || '';
        const dateParts = statementDateStr.split('/');
        statementDateObj = dateParts.length === 3 ? {
          month: parseInt(dateParts[0]),
          day: parseInt(dateParts[1]),
          year: parseInt(dateParts[2]),
          date: statementDateStr
        } : null;
      }
      
      // Ensure the statement date object has the correct structure
      if (statementDateObj && statementDateObj.date) {
        const dateStr = statementDateObj.date;
        const dateParts = dateStr.split('/');
        if (dateParts.length === 3) {
          statementDateObj = {
            month: parseInt(dateParts[0]),
            day: parseInt(dateParts[1]),
            year: parseInt(dateParts[2]),
            date: dateStr,
            ...statementDateObj // Keep any other properties like confidence, source
          };
        }
      }
      
      console.log('✅ Final statementDateObj to be sent:', statementDateObj);

      // Merge AI mappings with user mappings (including accepted mappings)
      const finalMappings = { ...userMappings };
      
      // Add accepted mappings
      acceptedMappings.forEach(mapping => {
        if (!finalMappings[mapping.field]) {
          finalMappings[mapping.field] = mapping.mapsTo;
        }
      });

   

      // STEP 1: Save Table Data
      setApprovalStep(0);
      setApprovalProgress(20);
      
      // CRITICAL FIX: Create a snapshot of current tables to ensure deleted rows are excluded
      console.log('🔍 DEBUG: Current tables state before snapshot:', {
        tableCount: tables.length,
        currentTableIdx: currentTableIdx,
        rowCounts: tables.map(t => t.rows?.length || 0),
        currentTableRowCount: tables[currentTableIdx]?.rows?.length || 0
      });
      
      // CRITICAL: Use current tables state, NOT extractedData.tables!
      // extractedData.tables contains the ORIGINAL unedited data
      const currentTablesSnapshot = tables.map(table => ({
        name: table.name || 'Unnamed Table',
        header: table.header || table.headers || [],
        rows: table.rows || [], // This will NOT include deleted rows
        summaryRows: Array.from(table.summaryRows || []), // Convert Set to Array
        extractor: table.extractor || 'manual',
        metadata: table.metadata || {}
      }));
      
      // Verification: Ensure we're not accidentally using original data
      if (extractedData.tables && extractedData.tables[0]?.rows?.length !== currentTablesSnapshot[0]?.rows?.length) {
        console.warn('⚠️ Row count mismatch detected!', {
          originalRows: extractedData.tables[0]?.rows?.length || 0,
          editedRows: currentTablesSnapshot[0]?.rows?.length || 0,
          difference: (extractedData.tables[0]?.rows?.length || 0) - (currentTablesSnapshot[0]?.rows?.length || 0)
        });
      }
      
      console.log('🔍 DEBUG: Saving tables snapshot:', {
        tableCount: currentTablesSnapshot.length,
        rowCounts: currentTablesSnapshot.map(t => t.rows.length),
        totalRows: currentTablesSnapshot.reduce((sum, t) => sum + t.rows.length, 0),
        firstTableRowCount: currentTablesSnapshot[0]?.rows?.length || 0
      });
      
      // Log the exact payload being sent to backend (use edited values)
      const saveTablesPayload = {
        upload_id: upload_id,
        tables: currentTablesSnapshot,
        company_id: carrier_id || company_id,
        selected_statement_date: statementDateObj,
        extracted_carrier: editedCarrierName || extractedData?.carrierName || extractedData?.extracted_carrier,
        extracted_date: editedStatementDate || extractedData?.extracted_date
      };
      
      console.log('📤 Sending save-tables request:', {
        upload_id,
        tableCount: saveTablesPayload.tables.length,
        firstTableRows: saveTablesPayload.tables[0]?.rows?.length || 0,
        firstTableHeaders: saveTablesPayload.tables[0]?.header?.length || 0,
        // Log first 3 rows for verification
        firstThreeRows: saveTablesPayload.tables[0]?.rows?.slice(0, 3) || []
      });
      
      const saveTablesResponse = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/table-editor/save-tables/`,
        saveTablesPayload,
        { withCredentials: true }
      );
      
      console.log('✅ Save-tables response:', saveTablesResponse.data);

      // ✅ CRITICAL: Get updated carrier_id from response (use edited value)
      const updatedCarrierId = saveTablesResponse.data?.carrier_id || carrier_id || company_id;
      const updatedCarrierName = saveTablesResponse.data?.carrier_name || editedCarrierName || extractedData?.carrierName || extractedData?.extracted_carrier;
      
      setApprovalProgress(40);

      // STEP 2: Learn Format Patterns
      setApprovalStep(1);
      
      try {
        // CRITICAL FIX: Use the same snapshot to ensure format learning uses edited data
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/table-editor/learn-format-patterns`,
          {
            upload_id: upload_id,
            tables: currentTablesSnapshot,
            company_id: updatedCarrierId, // Use updated carrier_id from save response
            selected_statement_date: statementDateObj,
            extracted_carrier: updatedCarrierName, // Already uses edited value
            extracted_date: editedStatementDate || extractedData?.extracted_date
          },
          { withCredentials: true }
        );
      } catch (learningError) {
        console.warn('⚠️ Format learning failed, continuing...', learningError);
        // Continue even if format learning fails
      }
      
      setApprovalProgress(60);

      // STEP 3: Save Field Mappings
      setApprovalStep(2);
      
      // Convert mappings to field config format for database fields
      const fieldConfig = Object.entries(finalMappings).map(([extractedField, mappedTo]) => ({
        display_name: mappedTo,
        source_field: extractedField
      }));

      // Get plan types from AI intelligence state (use edited value if available)
      const planTypes = editedPlanType 
        ? [editedPlanType] 
        : (aiIntelligence?.plan_type_detection?.detected_plan_types?.map(
            (pt: any) => pt.plan_type
          ) || []);

      // CRITICAL FIX: Use the snapshot for consistency
      const firstTable = currentTablesSnapshot[0] || {};
      const tableData = firstTable.rows || [];
      const headers = firstTable.header || [];

      // Build the payload matching backend MappingConfig schema
      const mappingPayload = {
        mapping: finalMappings,  // Direct field-to-field mappings
        plan_types: planTypes,
        field_config: databaseFields.map(field => ({
          display_name: field.display_name,
          description: field.description || ''
        })),
        table_data: tableData,
        headers: headers,
        selected_statement_date: statementDateObj
      };


      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/companies/${updatedCarrierId}/mapping/?upload_id=${upload_id}`, // Use updated carrier_id
        mappingPayload,
        { withCredentials: true }
      );

      setApprovalProgress(80);

      // STEP 4: Process Commission Data (Final Approval)
      setApprovalStep(3);
      
      // CRITICAL FIX: Use the SAME snapshot from Step 1 to ensure consistency
      // This guarantees deleted rows are NOT included in commission calculations
      const finalData = currentTablesSnapshot.map(table => {
        const tableHeaders = table.header;
        const tableRows = table.rows;
        
        // Convert each row from array to dictionary with header names as keys
        const transformedRows = tableRows.map((row: any[]) => {
          const rowDict: Record<string, any> = {};
          tableHeaders.forEach((header: string, index: number) => {
            rowDict[header] = row[index] || '';
          });
          return rowDict;
        });
        
        return {
          name: table.name,
          header: tableHeaders,
          rows: transformedRows,  // Now an array of dictionaries, WITHOUT deleted rows
          summaryRows: table.summaryRows  // CRITICAL: Include summary rows for backend filtering
        };
      });
      
      console.log('🔍 DEBUG: Final data for approval:', {
        tableCount: finalData.length,
        rowCounts: finalData.map(t => t.rows.length),
        totalRows: finalData.reduce((sum, t) => sum + t.rows.length, 0)
      });

      // planTypes already defined above in Step 3

      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/review/approve/`,
        {
          upload_id: upload_id,
          final_data: finalData,
          field_config: fieldConfig,
          plan_types: planTypes,
          selected_statement_date: statementDateObj
        },
        { withCredentials: true }
      );

      
      // STEP 5: Finalizing
      setApprovalStep(4);
      setApprovalProgress(100);
      
      // Show success message
      toast.success('Statement approved successfully! 🎉');
      
      // Wait a moment to show completion
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Redirect to carriers tab and open the specific carrier
      const carrierName = editedCarrierName || extractedData?.extracted_carrier || extractedData?.carrierName || extractedData?.document_metadata?.carrier_name;
      
      if (carrierName) {
        // Redirect to carriers tab with the specific carrier opened (using 'carrier' param for consistency with UploadPageContent)
        window.location.href = `/?tab=carriers&carrier=${encodeURIComponent(carrierName)}`;
      } else {
        // Final fallback: redirect to carriers tab
        window.location.href = '/?tab=carriers';
      }

    } catch (error: any) {
      console.error('❌ Submission error:', error);
      
      // Show specific error message
      const errorMessage = error?.response?.data?.detail || 
                          error?.response?.data?.message || 
                          error?.message || 
                          'Failed to approve statement';
      
      toast.error(`Error: ${errorMessage}`);
      setIsSubmitting(false);
    }
  };

  const handleMappingChange = (extractedField: string, newMapping: string) => {
    setUserMappings(prev => ({
      ...prev,
      [extractedField]: newMapping
    }));
  };

  const handleTablesChange = (updatedTables: any[]) => {
    // Normalize tables to ensure summaryRows is a Set
    const normalizedTables = updatedTables.map(table => ({
      ...table,
      summaryRows: table.summaryRows instanceof Set 
        ? table.summaryRows 
        : new Set(Array.isArray(table.summaryRows) ? table.summaryRows : [])
    }));
    
    console.log('📝 Tables updated:', {
      tableCount: normalizedTables.length,
      rowCounts: normalizedTables.map(t => t.rows?.length || 0),
      currentTableRows: normalizedTables[currentTableIdx]?.rows?.length || 0
    });
    
    setTables(normalizedTables);
    onDataUpdate({ ...extractedData, tables: normalizedTables });
  };

  // Handle accepting a single mapping
  const handleAcceptMapping = (mapping: FieldMapping) => {
    const tableHeaders = tables?.[0]?.header || tables?.[0]?.headers || [];
    const colIndex = tableHeaders.findIndex((h: string) => 
      h.toLowerCase() === mapping.extracted_field.toLowerCase()
    );
    const sampleData = colIndex >= 0 && tables?.[0]?.rows?.[0] 
      ? tables[0].rows[0][colIndex] 
      : 'N/A';

    // Check if already accepted
    if (acceptedMappings.some(m => m.field === mapping.extracted_field)) {
      return; // Already accepted
    }

    const newMapping = {
      field: mapping.extracted_field,
      mapsTo: mapping.mapped_to,
      confidence: mapping.confidence,
      sample: sampleData
    };

    setAcceptedMappings(prev => [...prev, newMapping]);
    setNewlyAddedField(mapping.extracted_field);
    
    // Clear animation after 1 second
    setTimeout(() => setNewlyAddedField(null), 1000);
    
    // Also update user mappings
    handleMappingChange(mapping.extracted_field, mapping.mapped_to);
  };

  const handleSkipMapping = (mapping: FieldMapping) => {
    const tableHeaders = tables?.[0]?.header || tables?.[0]?.headers || [];
    const colIndex = tableHeaders.findIndex((h: string) => 
      h.toLowerCase() === mapping.extracted_field.toLowerCase()
    );
    const sampleData = colIndex >= 0 && tables?.[0]?.rows?.[0] 
      ? tables[0].rows[0][colIndex] 
      : 'N/A';

    // Check if already skipped
    if (skippedFields.some(m => m.field === mapping.extracted_field)) {
      return; // Already skipped
    }

    const newSkippedMapping = {
      field: mapping.extracted_field,
      mapsTo: mapping.mapped_to,
      confidence: mapping.confidence,
      sample: sampleData
    };

    // Add to skipped fields
    setSkippedFields(prev => [...prev, newSkippedMapping]);
    
    // Remove from accepted mappings if it was previously accepted
    setAcceptedMappings(prev => prev.filter(m => m.field !== mapping.extracted_field));
    
    // Remove from user mappings
    setUserMappings(prev => {
      const updated = { ...prev };
      delete updated[mapping.extracted_field];
      return updated;
    });
  };

  // Handle putting back a skipped field
  const handlePutBackSkippedField = (skippedMapping: {field: string, mapsTo: string, confidence: number, sample: string}) => {
    // Remove from skipped fields
    setSkippedFields(prev => prev.filter(m => m.field !== skippedMapping.field));
    
    // The field will now appear back in the left panel as a normal field mapping suggestion
    toast.success(`↩ Put back: ${skippedMapping.field}`);
  };

  // Handle accepting all high confidence mappings
  const handleAcceptAllMappings = () => {
    const highConfidenceMappings = aiMappings.filter(m => m.confidence >= 0.8);
    const tableHeaders = tables?.[0]?.header || tables?.[0]?.headers || [];
    
    const newMappings = highConfidenceMappings
      .filter(mapping => !acceptedMappings.some(m => m.field === mapping.extracted_field))
      .map(mapping => {
        const colIndex = tableHeaders.findIndex((h: string) => 
          h.toLowerCase() === mapping.extracted_field.toLowerCase()
        );
        const sampleData = colIndex >= 0 && tables?.[0]?.rows?.[0] 
          ? tables[0].rows[0][colIndex] 
          : 'N/A';

        return {
          field: mapping.extracted_field,
          mapsTo: mapping.mapped_to,
          confidence: mapping.confidence,
          sample: sampleData
        };
      });

    setAcceptedMappings(prev => [...prev, ...newMappings]);
    
    // Animate each one sequentially
    newMappings.forEach((mapping, index) => {
      setTimeout(() => {
        setNewlyAddedField(mapping.field);
        setTimeout(() => setNewlyAddedField(null), 800);
      }, index * 150);
    });

    // Update user mappings for all
    const mappingsUpdate: Record<string, string> = {};
    newMappings.forEach(mapping => {
      mappingsUpdate[mapping.field] = mapping.mapsTo;
    });
    setUserMappings(prev => ({ ...prev, ...mappingsUpdate }));
  };

  // Handle custom mapping selection
  const handleCustomMapping = (extractedField: string, selectedHeader: string, databaseField?: string) => {
    const tableHeaders = tables?.[0]?.header || tables?.[0]?.headers || [];
    // Get sample data from the EXTRACTED field (the column in the table), not the database field
    const colIndex = tableHeaders.findIndex((h: string) => 
      h.toLowerCase() === extractedField.toLowerCase()
    );
    const sampleData = colIndex >= 0 && tables?.[0]?.rows?.[0] 
      ? tables[0].rows[0][colIndex] 
      : 'N/A';

    // Use the databaseField if provided, otherwise fall back to selectedHeader
    const targetField = databaseField || selectedHeader;

    // Find if already accepted and update it
    const existingIndex = acceptedMappings.findIndex(m => m.field === extractedField);
    if (existingIndex >= 0) {
      const updated = [...acceptedMappings];
      updated[existingIndex] = {
        ...updated[existingIndex],
        mapsTo: targetField,
        sample: sampleData
      };
      setAcceptedMappings(updated);
    } else {
      // Add new mapping
      setAcceptedMappings(prev => [...prev, {
        field: extractedField,
        mapsTo: targetField,
        confidence: 1.0, // User selected, so 100%
        sample: sampleData
      }]);
      setNewlyAddedField(extractedField);
      setTimeout(() => setNewlyAddedField(null), 1000);
    }

    // Also update the AI mappings in aiIntelligence state so left panel reflects the change
    if (aiIntelligence?.field_mapping?.mappings) {
      const updatedMappings = aiIntelligence.field_mapping.mappings.map(m => 
        m.extracted_field === extractedField 
          ? { ...m, mapped_to: targetField, confidence: 1.0 }
          : m
      );
      setAiIntelligence({
        ...aiIntelligence,
        field_mapping: {
          ...aiIntelligence.field_mapping,
          mappings: updatedMappings
        }
      });
    }

    handleMappingChange(extractedField, targetField);
  };

  // Handle removing an accepted mapping
  const handleRemoveMapping = (fieldName: string) => {
    setAcceptedMappings(prev => prev.filter(m => m.field !== fieldName));
    
    // Also remove from user mappings
    setUserMappings(prev => {
      const updated = { ...prev };
      delete updated[fieldName];
      return updated;
    });
  };

  // Handle GPT extraction
  const handleExtractWithGPT = async () => {
    setIsExtractingWithGPT(true);
    
    try {
      const upload_id = uploadData?.upload_id || uploadData?.id || extractedData?.upload_id;
      const company_id = uploadData?.company_id || extractedData?.company_id || extractedData?.carrier_id;
      
      if (!upload_id || !company_id) {
        throw new Error('Missing upload_id or company_id');
      }

      
      // Call the GPT extraction endpoint
      const formData = new FormData();
      formData.append('upload_id', upload_id);
      formData.append('company_id', company_id);
      
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/extract-tables-gpt/`,
        formData,
        { 
          withCredentials: true,
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      if (response.data.success) {
        
        // Update tables with the new extraction
        const newTables = (response.data.tables || []).map((table: any) => ({
          ...table,
          summaryRows: table.summaryRows instanceof Set 
            ? table.summaryRows 
            : new Set(Array.isArray(table.summaryRows) ? table.summaryRows : [])
        }));
        const newDocumentMetadata = response.data.document_metadata || {};
        
        // Update local state
        setTables(newTables);
        
        // Update parent with new extraction data including document_metadata
        const updatedExtractedData = { 
          ...extractedData, 
          tables: newTables,
          extraction_method: 'gpt4o_vision_enhanced',
          document_metadata: newDocumentMetadata,
          carrierName: newDocumentMetadata.carrier_name || extractedData.carrierName,
          statementDate: newDocumentMetadata.statement_date || extractedData.statementDate,
        };
        
        // Update edited metadata state with new values
        if (newDocumentMetadata.carrier_name) {
          setEditedCarrierName(newDocumentMetadata.carrier_name);
        }
        if (newDocumentMetadata.statement_date) {
          setEditedStatementDate(newDocumentMetadata.statement_date);
        }
        
        onDataUpdate(updatedExtractedData);
        
        toast.success(`GPT extraction completed! Extracted ${newTables.length} table(s) with metadata`);
      } else {
        throw new Error(response.data.error || 'GPT extraction failed');
      }
    } catch (error: any) {
      console.error('❌ GPT extraction error:', error);
      const errorMessage = error?.response?.data?.detail || 
                          error?.response?.data?.message || 
                          error?.message || 
                          'Failed to extract with GPT';
      toast.error(`Error: ${errorMessage}`);
    } finally {
      setIsExtractingWithGPT(false);
    }
  };

  // Handle table switching in field mapping mode
  const handleTableSwitch = async (newIndex: number) => {
    if (newIndex === currentTableIdx || newIndex < 0 || newIndex >= tables.length) {
      return;
    }

    // Update the current table index
    setCurrentTableIdx(newIndex);
    
    // Clear accepted mappings when switching tables as they're table-specific
    setAcceptedMappings([]);
    setUserMappings({});
    
    toast.success(`Switched to Table ${newIndex + 1}. Please review and accept field mappings for this table.`);
    
    // Note: If backend AI re-mapping is needed, add API call here
    // For now, we just switch the visible table and user can manually map fields
  };

  return (
    <>
      {/* Premium Progress Loader - Shows during submission OR AI mapping */}
      <PremiumProgressLoader
        currentStep={isLoadingAIMapping ? aiMappingStep : approvalStep}
        steps={isLoadingAIMapping ? AI_MAPPING_STEPS : APPROVAL_STEPS}
        progress={isLoadingAIMapping ? aiMappingProgress : approvalProgress}
        isVisible={isSubmitting || isLoadingAIMapping}
      />

      <div className="h-screen bg-gray-50 dark:bg-slate-900 flex flex-col overflow-hidden">
        
        {/* Premium Header */}
      <div className="bg-white dark:bg-slate-800 shadow-sm border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex-shrink-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              {viewMode === 'table_review' ? (
                <>
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h1 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Review Extracted Data</h1>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Verify and edit table contents</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                  <Map className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h1 className="text-lg font-semibold text-gray-900 dark:text-slate-100">AI Field Mapping</h1>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Review intelligent field suggestions</p>
                  </div>
                </>
              )}
            </div>
            
            {/* Progress Indicator */}
            <div className="flex items-center space-x-2 ml-4 px-3 py-1.5 bg-gray-100 dark:bg-slate-700 rounded-full">
              <div className={`w-2 h-2 rounded-full ${viewMode === 'table_review' ? 'bg-blue-600 animate-pulse' : 'bg-green-600'}`} />
              <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                Step {viewMode === 'table_review' ? '1' : '2'} of 2
              </span>
            </div>

            {/* Plan Type Detection - Compact */}
            {viewMode === 'field_mapping' && aiIntelligence?.plan_type_detection && (
              <div className="ml-4 px-2 py-1">
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  <div>
                    <span className="text-xs text-purple-600 dark:text-purple-400 font-semibold block">Plan Type</span>
                    <span className="text-sm font-bold text-gray-900 dark:text-slate-100">
                      {aiIntelligence.plan_type_detection.detected_plan_types[0]?.plan_type || 'Unknown'}
                    </span>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ml-2 ${
                    aiIntelligence.plan_type_detection.confidence >= 0.8 ? 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400' :
                    aiIntelligence.plan_type_detection.confidence >= 0.6 ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                    'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                  }`}>
                    {Math.round(aiIntelligence.plan_type_detection.confidence * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>
          
          {/* Metadata Display - Professional Cards with Borders and Backgrounds */}
          <div className="flex items-center space-x-3">
            {/* Carrier Name - Editable */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-700 rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 block uppercase tracking-wide mb-1">Carrier</span>
              {isEditingMetadata ? (
                <input
                  type="text"
                  value={editedCarrierName}
                  onChange={(e) => setEditedCarrierName(e.target.value)}
                  className="text-sm font-bold text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-800 border border-blue-300 dark:border-blue-600 rounded px-2 py-1 w-40"
                  placeholder="Enter carrier name"
                />
              ) : (
                <span className="text-sm font-bold text-blue-900 dark:text-blue-100 block">
                  {editedCarrierName || 'Unknown'}
                </span>
              )}
            </div>
            
            {/* Broker - Display Only */}
            <div className="bg-purple-50 dark:bg-purple-900/20 border-2 border-purple-200 dark:border-purple-700 rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 block uppercase tracking-wide mb-1">Broker</span>
              <span className="text-sm font-bold text-purple-900 dark:text-purple-100 block">
                {extractedData?.document_metadata?.broker_company || 'Not detected'}
              </span>
            </div>
            
            {/* Plan Type - Editable */}
            <div className="bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-700 rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-green-600 dark:text-green-400 block uppercase tracking-wide mb-1">Plan Type</span>
              {isEditingMetadata ? (
                <input
                  type="text"
                  value={editedPlanType}
                  onChange={(e) => setEditedPlanType(e.target.value)}
                  className="text-sm font-bold text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-800 border border-green-300 dark:border-green-600 rounded px-2 py-1 w-40"
                  placeholder="Enter plan type"
                />
              ) : (
                <span className="text-sm font-bold text-green-900 dark:text-green-100 block">
                  {editedPlanType || 'Not detected'}
                </span>
              )}
            </div>
            
            {/* Statement Date - Editable with Datepicker */}
            <div className="bg-orange-50 dark:bg-orange-900/20 border-2 border-orange-200 dark:border-orange-700 rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-orange-600 dark:text-orange-400 block uppercase tracking-wide mb-1">Statement Date</span>
              {isEditingMetadata ? (
                <input
                  type="date"
                  value={editedStatementDate ? (() => {
                    // Convert MM/DD/YYYY to YYYY-MM-DD for date input
                    const parts = editedStatementDate.split('/');
                    if (parts.length === 3) {
                      return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`;
                    }
                    return '';
                  })() : ''}
                  onChange={(e) => {
                    // Convert YYYY-MM-DD to MM/DD/YYYY
                    const dateValue = e.target.value;
                    if (dateValue) {
                      const [year, month, day] = dateValue.split('-');
                      setEditedStatementDate(`${month}/${day}/${year}`);
                    } else {
                      setEditedStatementDate('');
                    }
                  }}
                  className="text-sm font-bold text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-800 border border-orange-300 dark:border-orange-600 rounded px-2 py-1 w-36"
                />
              ) : (
                <span className="text-sm font-bold text-orange-900 dark:text-orange-100 block">
                  {editedStatementDate || 'Not detected'}
                </span>
              )}
            </div>
            
            {/* Edit/Save Button */}
            <button
              onClick={() => {
                if (isEditingMetadata) {
                  // Save changes
                  toast.success('Metadata updated! These values will be used throughout the workflow and saved in format learning.', {
                    duration: 4000
                  });
                }
                setIsEditingMetadata(!isEditingMetadata);
              }}
              className={`px-4 py-2.5 rounded-lg shadow-md hover:shadow-lg transition-all font-semibold text-sm ${
                isEditingMetadata 
                  ? 'bg-green-500 dark:bg-green-600 text-white border border-green-600 dark:border-green-700' 
                  : 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 border border-gray-300 dark:border-slate-600'
              }`}
              title={isEditingMetadata ? 'Save changes' : 'Edit carrier, plan type, or date'}
            >
              {isEditingMetadata ? '✓ Save' : '✏️ Edit'}
            </button>
            
            {viewMode === 'field_mapping' && (
              <div className="px-2 py-1">
                <span className="text-xs font-medium text-green-600 dark:text-green-400 block uppercase tracking-wide mb-0.5">Accepted</span>
                <span className="text-base font-bold text-green-900 dark:text-green-100">
                  {acceptedMappings.length} fields
                </span>
              </div>
            )}
            
            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(actualTheme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              aria-label={`Switch to ${actualTheme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {actualTheme === 'dark' ? <Sun className="w-5 h-5 text-slate-500 dark:text-slate-400" /> : <Moon className="w-5 h-5 text-slate-500 dark:text-slate-400" />}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area - Premium 2-Column Layout */}
      <div className="flex-1 flex overflow-hidden min-w-0">
        
        {/* Left Panel - Document/Data Preview */}
        {viewMode === 'table_review' && (
          <div className={`${isPreviewCollapsed ? 'w-0' : 'w-[30%]'} flex-shrink-0 transition-all duration-300`}>
            <PDFViewer
              fileUrl={extractedData?.gcs_url || extractedData?.file_name || ''}
              isCollapsed={isPreviewCollapsed}
              onToggleCollapse={() => setIsPreviewCollapsed(!isPreviewCollapsed)}
            />
          </div>
        )}

        {viewMode === 'field_mapping' && !isPreviewCollapsed && (
        <div className={`bg-white dark:bg-slate-800 border-r-2 border-gray-200 dark:border-slate-700 flex flex-col transition-all duration-700 ease-in-out w-[30%] ${
          isTransitioning ? 'opacity-50' : 'opacity-100'
        }`}>

          {/* Left Panel Content */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {(
              // Show Table + Field Mapping Suggestions in field mapping mode
              <div className={`h-full overflow-auto p-4 space-y-4 transition-opacity duration-500 ${
                isTransitioning ? 'opacity-0' : 'opacity-100'
              }`}>
                {/* Extracted Table Preview */}
                <div className="bg-gray-50 dark:bg-slate-800 rounded-lg p-3 border border-gray-200 dark:border-slate-700">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                    Extracted Table Preview
                    {tables.length > 1 && (
                      <span className="ml-2 text-xs text-gray-500 dark:text-slate-400">
                        (Table {currentTableIdx + 1} of {tables.length})
                      </span>
                    )}
                  </h4>
                  <div className="text-xs text-gray-600 dark:text-slate-400">
                    {tables?.[currentTableIdx]?.headers?.length || tables?.[currentTableIdx]?.header?.length || 0} columns × {tables?.[currentTableIdx]?.rows?.length || 0} rows
                  </div>
                </div>
                
                {/* Compact Table Display */}
                {tables?.[currentTableIdx] && (
                  <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 overflow-hidden shadow-sm">
                    <div className="overflow-x-auto max-h-64">
                      <table className="min-w-full text-xs company-table">
                        <thead className="bg-gray-50 dark:bg-slate-700 sticky top-0">
                          <tr>
                            {(tables[currentTableIdx].headers || tables[currentTableIdx].header || []).map((header: string, idx: number) => (
                              <th key={idx} className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700">
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {(tables[currentTableIdx].rows || []).slice(0, 4).map((row: string[], rowIdx: number) => (
                            <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
                              {row.map((cell: string, cellIdx: number) => (
                                <td key={cellIdx} className="px-3 py-2 border-b border-gray-100 dark:border-slate-600 text-gray-600 dark:text-slate-300">
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {(tables[currentTableIdx].rows?.length || 0) > 4 && (
                      <div className="p-2 bg-gray-50 dark:bg-slate-700 text-xs text-gray-500 dark:text-slate-400 text-center border-t border-gray-200 dark:border-slate-600">
                        Showing 4 of {tables[currentTableIdx].rows?.length} rows
                      </div>
                    )}
                  </div>
                )}

                {/* Enhanced AI Mapper with Table Selection - ALWAYS VISIBLE WHEN LOADING */}
                {isLoadingAIMapping ? (
                  <div className="flex items-center justify-center py-12 opacity-100">
                    <div className="text-center">
                      <div className="w-20 h-20 border-4 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                      <h3 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-3">🤖 AI Field Mapping</h3>
                      <p className="text-base text-gray-700 dark:text-slate-300 font-medium mb-2">Generating intelligent field mappings...</p>
                      <p className="text-sm text-gray-600 dark:text-slate-400">Analyzing your edited table data</p>
                    </div>
                  </div>
                ) : aiIntelligence?.enabled ? (
                  <EnhancedAIMapper
                    tables={tables}
                    currentTableIndex={currentTableIdx}
                    aiIntelligence={aiIntelligence}
                    uploadId={uploadData?.upload_id || uploadData?.id || extractedData?.upload_id}
                    onTableSwitch={handleTableSwitch}
                    tableHeaders={tables?.[currentTableIdx]?.header || tables?.[currentTableIdx]?.headers || []}
                    databaseFields={databaseFields}
                    acceptedFields={acceptedMappings.map(m => m.field)}
                    skippedFields={skippedFields.map(m => m.field)}
                    onAcceptMapping={handleAcceptMapping}
                    onSkipMapping={handleSkipMapping}
                    onAcceptAllMappings={handleAcceptAllMappings}
                    onCustomMapping={handleCustomMapping}
                    onReviewMappings={() => console.log('Review mappings')}
                  />
                ) : (
                  <div className="text-center py-8">
                    <p className="text-sm text-gray-600 dark:text-slate-400">No AI field mappings available. You can manually map fields.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        )}

        {/* Right Panel - Table Data/Field Mapping */}
        <div className={`${isPreviewCollapsed ? 'flex-1' : viewMode === 'table_review' ? 'w-[70%]' : 'w-[70%]'} bg-gray-50 dark:bg-slate-900 flex flex-col transition-all duration-700 ease-in-out flex-shrink-0 min-w-0 ${
          isTransitioning ? 'opacity-50' : 'opacity-100'
        }`}>
          
          {/* Right Panel Header */}
          <div className="px-6 py-2 border-b-2 border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {viewMode === 'table_review' ? (
                  <>
                    <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                      <Table2 className="w-4 h-4 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-slate-100">Extracted Table Data</h3>
                      <p className="text-xs text-gray-500 dark:text-slate-400">Review and edit extracted values</p>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                      <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-slate-100">Accepted Field Mappings</h3>
                      <p className="text-xs text-gray-500 dark:text-slate-400">Fields you&apos;ve confirmed for database import</p>
                    </div>
                  </>
                )}
              </div>
              
              {/* Action Buttons */}
              {viewMode === 'table_review' && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleExtractWithGPT}
                    disabled={isExtractingWithGPT}
                    className="flex items-center space-x-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    title="Extract with GPT-4o Vision for improved accuracy"
                  >
                    {isExtractingWithGPT ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Extracting...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span>Extract with GPT</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Table Navigation Controls - Show when multiple tables exist in table review mode */}
            {viewMode === 'table_review' && tables && tables.length > 1 && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setCurrentTableIdx(Math.max(0, currentTableIdx - 1))}
                      disabled={currentTableIdx === 0}
                      className="px-3 py-1.5 text-sm bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-gray-700 dark:text-slate-300"
                    >
                      ← Previous
                    </button>
                    
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-600 dark:text-slate-400">Table</span>
                      <select
                        value={currentTableIdx}
                        onChange={(e) => setCurrentTableIdx(Number(e.target.value))}
                        className="px-3 py-1.5 border border-gray-300 dark:border-slate-600 rounded-md text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-100"
                      >
                        {tables.map((table, idx) => (
                          <option key={idx} value={idx}>
                            {idx + 1} - {table.name || `Table ${idx + 1}`}
                          </option>
                        ))}
                      </select>
                      <span className="text-sm text-gray-600 dark:text-slate-400">of {tables.length}</span>
                    </div>
                    
                    <button
                      onClick={() => setCurrentTableIdx(Math.min(tables.length - 1, currentTableIdx + 1))}
                      disabled={currentTableIdx === tables.length - 1}
                      className="px-3 py-1.5 text-sm bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-gray-700 dark:text-slate-300"
                    >
                      Next →
                    </button>

                    {/* Delete Current Table Button */}
                    <button
                      onClick={() => {
                        if (window.confirm(`Are you sure you want to delete "${tables[currentTableIdx]?.name || `Table ${currentTableIdx + 1}`}"?\n\nThis action cannot be undone.`)) {
                          const newTables = tables.filter((_, idx) => idx !== currentTableIdx);
                          handleTablesChange(newTables);
                          // Adjust currentTableIdx if needed
                          if (currentTableIdx >= newTables.length) {
                            setCurrentTableIdx(Math.max(0, newTables.length - 1));
                          }
                          toast.success('Table deleted successfully');
                        }
                      }}
                      className="px-3 py-1.5 text-sm bg-white dark:bg-slate-800 border border-red-300 dark:border-red-600 text-red-600 dark:text-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 hover:border-red-400 dark:hover:border-red-500 transition-colors font-medium flex items-center gap-1.5"
                      title="Delete this table"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete Table
                    </button>
                  </div>

                  {/* Current table info */}
                  <div className="text-xs text-gray-500 dark:text-slate-400">
                    {tables[currentTableIdx]?.rows?.length || 0} rows × {(tables[currentTableIdx]?.header || tables[currentTableIdx]?.headers || []).length} columns
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel Content */}
          <div className="flex-1 w-full min-w-0 overflow-hidden">
            {viewMode === 'table_review' ? (
              // Show new ExtractedDataTable in review mode
              <div className={`h-full w-full transition-opacity duration-500 ${
                isTransitioning ? 'opacity-0' : 'opacity-100'
              }`}>
                {tables && tables.length > 0 && tables[currentTableIdx] && (
                  <ExtractedDataTable
                    table={tables[currentTableIdx]}
                    onTableChange={(updatedTable) => {
                      const updatedTables = [...tables];
                      updatedTables[currentTableIdx] = updatedTable;
                      handleTablesChange(updatedTables);
                    }}
                    showSummaryRows={showSummaryRows}
                    onToggleSummaryRows={() => setShowSummaryRows(!showSummaryRows)}
                  />
                )}
                {tables && tables.length === 0 && (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <div className="text-gray-500 text-lg">No tables available</div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              // Show Accepted Mappings Table in mapping mode
              <div className={`h-full flex flex-col transition-opacity duration-500 ${
                isTransitioning ? 'opacity-0' : 'opacity-100'
              }`}>
                {acceptedMappings.length === 0 ? (
                  // Empty State
                  <div className="flex-1 flex items-center justify-center p-8">
                    <div className="text-center max-w-md">
                      <div className="w-20 h-20 bg-gray-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg className="w-10 h-10 text-gray-400 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                        </svg>
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">No Fields Accepted Yet</h3>
                      <p className="text-sm text-gray-600 dark:text-slate-400 mb-4">
                        Click the <span className="inline-flex items-center mx-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded text-xs font-medium">✓ Accept</span> button on field mappings in the left panel to add them here
                      </p>
                      <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3 text-left">
                        <p className="text-xs text-blue-800 dark:text-blue-300 font-medium mb-1">💡 Tip</p>
                        <p className="text-xs text-blue-700 dark:text-blue-300">
                          You can also click &quot;Accept All High Confidence&quot; to quickly accept all mappings with 85%+ confidence
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Accepted Mappings Table
                  <div className="flex-1 overflow-auto p-4">
                    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 overflow-hidden shadow-sm">
                      <div className="overflow-auto max-h-full">
                        <table className="min-w-full text-sm company-table">
                          <thead className="bg-gray-50 dark:bg-slate-700 sticky top-0">
                            <tr>
                              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700">Extracted Field</th>
                              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700">Maps To</th>
                              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700">Confidence</th>
                              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700">Sample Data</th>
                              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700 w-20">Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {acceptedMappings.map((mapping, idx) => (
                              <tr 
                                key={mapping.field}
                                className={`transition-colors ${
                                  newlyAddedField === mapping.field 
                                    ? 'bg-blue-50 dark:bg-blue-900/20 animate-pulse' 
                                    : 'hover:bg-gray-50 dark:hover:bg-slate-700'
                                }`}
                                style={{
                                  animation: newlyAddedField === mapping.field 
                                    ? 'slideIn 0.5s ease-out' 
                                    : undefined
                                }}
                              >
                                <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600">
                                  <div className="flex items-center space-x-2">
                                    <svg className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span className="font-mono text-sm text-gray-900 dark:text-slate-100">{mapping.field}</span>
                                  </div>
                                </td>
                                <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600 text-gray-600 dark:text-slate-300">{mapping.mapsTo}</td>
                                <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600">
                                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                                    mapping.confidence >= 0.8 ? 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400' :
                                    mapping.confidence >= 0.6 ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                                    'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                                  }`}>
                                    {Math.round(mapping.confidence * 100)}%
                                  </span>
                                </td>
                                <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600 text-gray-600 dark:text-slate-300 font-mono max-w-xs truncate" title={mapping.sample}>
                                  {mapping.sample || <span className="text-gray-400 dark:text-slate-500">N/A</span>}
                                </td>
                                <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600">
                                  <button
                                    onClick={() => {
                                      handleRemoveMapping(mapping.field);
                                      toast.success(`Removed: ${mapping.field}`);
                                    }}
                                    className="p-1.5 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                                    title="Remove mapping"
                                    type="button"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="p-2 bg-gray-50 dark:bg-slate-700 text-xs text-gray-500 dark:text-slate-400 text-center border-t border-gray-200 dark:border-slate-600">
                        <span className="text-gray-600 dark:text-slate-300 font-medium">
                          {acceptedMappings.length} field{acceptedMappings.length !== 1 ? 's' : ''} accepted
                        </span>
                        <span className="ml-2 text-gray-500 dark:text-slate-400">
                          • {aiMappings.length - acceptedMappings.length - skippedFields.length} remaining
                        </span>
                      </div>
                    </div>

                    {/* Skipped Fields Table */}
                    {skippedFields.length > 0 && (
                      <div className="mt-4 bg-white dark:bg-slate-800 rounded-lg border border-orange-200 dark:border-orange-700 overflow-hidden shadow-sm">
                        <div className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 px-4 py-2 border-b border-orange-200 dark:border-orange-700">
                          <div className="flex items-center space-x-2">
                            <svg className="w-5 h-5 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                            <div>
                              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                                Skipped Fields
                              </h4>
                              <p className="text-xs text-gray-600 dark:text-gray-400">
                                Fields you chose to skip from mapping
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="overflow-auto max-h-64">
                          <table className="min-w-full text-sm">
                            <thead className="bg-gray-50 dark:bg-slate-700 sticky top-0">
                              <tr>
                                <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600">Extracted Field</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600">Would Map To</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600">Confidence</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600">Sample Data</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600 w-20">Action</th>
                              </tr>
                            </thead>
                            <tbody>
                              {skippedFields.map((mapping, idx) => (
                                <tr 
                                  key={mapping.field}
                                  className="hover:bg-orange-50 dark:hover:bg-orange-900/10 transition-colors"
                                >
                                  <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600">
                                    <div className="flex items-center space-x-2">
                                      <svg className="w-4 h-4 text-orange-600 dark:text-orange-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                      </svg>
                                      <span className="font-mono text-sm text-gray-900 dark:text-slate-100">{mapping.field}</span>
                                    </div>
                                  </td>
                                  <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600 text-gray-600 dark:text-slate-300">{mapping.mapsTo}</td>
                                  <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600">
                                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                                      mapping.confidence >= 0.8 ? 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400' :
                                      mapping.confidence >= 0.6 ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                                      'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                                    }`}>
                                      {Math.round(mapping.confidence * 100)}%
                                    </span>
                                  </td>
                                  <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600 text-gray-600 dark:text-slate-300 font-mono max-w-xs truncate" title={mapping.sample}>
                                    {mapping.sample || <span className="text-gray-400 dark:text-slate-500">N/A</span>}
                                  </td>
                                  <td className="px-3 py-2 border-b border-gray-100 dark:border-slate-600">
                                    <button
                                      onClick={() => {
                                        handlePutBackSkippedField(mapping);
                                      }}
                                      className="p-1.5 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded transition-colors"
                                      title="Put back this field"
                                      type="button"
                                    >
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                                      </svg>
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <div className="p-2 bg-orange-50 dark:bg-orange-900/20 text-xs text-orange-800 dark:text-orange-400 text-center border-t border-orange-200 dark:border-orange-700">
                          <span className="font-medium">
                            {skippedFields.length} field{skippedFields.length !== 1 ? 's' : ''} skipped
                          </span>
                          <span className="ml-2">
                            • Click the <svg className="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg> button to put back
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Bar - Context Sensitive */}
      <ActionBar
        viewMode={viewMode}
        mappingStats={mappingStats}
        onModeChange={handleModeTransition}
        onFinalSubmit={handleFinalSubmission}
        isSubmitting={isSubmitting}
        canProceed={
          // Allow submission if:
          // 1. No fields need review, OR
          // 2. All non-skipped AI mappings have been explicitly accepted by the user
          mappingStats.needsReview === 0 || 
          acceptedMappings.length >= (aiMappings.length - skippedFields.length)
        }
        isTransitioning={isTransitioning}
        carrierName={editedCarrierName}
        statementDate={editedStatementDate}
      />
    </div>
    </>
  );
}
