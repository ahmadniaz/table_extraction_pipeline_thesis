/**
 * AI Intelligent Mapping Service
 * 
 * This service provides AI-powered field mapping and plan type detection
 * for the commission tracker upload flow.
 * 
 * Features:
 * - Real-time AI field mapping suggestions
 * - Intelligent plan type detection
 * - Confidence scoring and alternatives
 * - User correction learning
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface FieldMapping {
  extracted_field: string;
  mapped_to: string;
  mapped_to_column: string;
  database_field_id: string;
  confidence: number;
  reasoning: string;
  alternatives?: Array<{
    field: string;
    confidence: number;
    reasoning: string;
  }>;
  requires_review: boolean;
}

export interface PlanTypeDetection {
  plan_type: string;
  plan_type_id: string;
  confidence: number;
  reasoning: string;
  evidence: string[];
  requires_review: boolean;
}

export interface AIFieldMappingRequest {
  extracted_headers: string[];
  table_sample_data: string[][];
  carrier_id?: string;
  document_context?: {
    carrier_name?: string;
    statement_date?: string;
    document_type?: string;
  };
}

export interface AIPlanTypeDetectionRequest {
  document_context: {
    carrier_name?: string;
    statement_date?: string;
    document_type?: string;
  };
  table_headers: string[];
  table_sample_data: string[][];
  extracted_carrier?: string;
}

export interface AIFieldMappingResponse {
  success: boolean;
  mappings: FieldMapping[];
  unmapped_fields: string[];
  overall_confidence: number;
  reasoning: Record<string, any>;
  statistics: {
    total_fields: number;
    mapped_count: number;
    unmapped_count: number;
    high_confidence_count: number;
    medium_confidence_count: number;
    low_confidence_count: number;
  };
  learned_format_used: boolean;
  timestamp: string;
}

export interface AIPlanTypeDetectionResponse {
  success: boolean;
  detected_plan_types: PlanTypeDetection[];
  overall_confidence: number;
  reasoning: Record<string, any>;
  multi_plan_document: boolean;
  statistics: {
    total_detected: number;
    high_confidence_count: number;
    medium_confidence_count: number;
    low_confidence_count: number;
    requires_review: boolean;
  };
  timestamp: string;
}

export interface EnhancedExtractionAnalysisResponse {
  success: boolean;
  field_mapping: {
    success: boolean;
    mappings: FieldMapping[];
    unmapped_fields: string[];
    confidence: number;
    learned_format_used: boolean;
  };
  plan_type_detection: {
    success: boolean;
    detected_plan_types: PlanTypeDetection[];
    confidence: number;
    multi_plan_document: boolean;
  };
  overall_confidence: number;
  analysis_complete: boolean;
  timestamp: string;
}

/**
 * Get AI-powered field mapping suggestions
 */
export async function getAIFieldMappings(
  request: AIFieldMappingRequest,
  token: string
): Promise<AIFieldMappingResponse> {
  try {
    console.log('🤖 AI Mapping: Requesting field mappings', {
      headers_count: request.extracted_headers.length,
      has_carrier: !!request.carrier_id,
      has_context: !!request.document_context
    });

    const response = await fetch(`${API_BASE_URL}/api/ai/map-fields`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include',
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'AI field mapping failed');
    }

    const data = await response.json();
    console.log('✅ AI Mapping: Received field mappings', {
      mappings_count: data.mappings?.length || 0,
      confidence: data.overall_confidence,
      unmapped: data.unmapped_fields?.length || 0
    });

    return data;
  } catch (error) {
    console.error('AI field mapping error:', error);
    throw error;
  }
}

/**
 * Get AI-powered plan type detection
 */
export async function getAIPlanTypeDetection(
  request: AIPlanTypeDetectionRequest,
  token: string
): Promise<AIPlanTypeDetectionResponse> {
  try {
    console.log('🔍 AI Plan Detection: Requesting plan type detection', {
      headers_count: request.table_headers.length,
      has_carrier: !!request.extracted_carrier
    });

    const response = await fetch(`${API_BASE_URL}/api/ai/detect-plan-types`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include',
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'AI plan type detection failed');
    }

    const data = await response.json();
    console.log('✅ AI Plan Detection: Received plan types', {
      detected_count: data.detected_plan_types?.length || 0,
      confidence: data.overall_confidence,
      multi_plan: data.multi_plan_document
    });

    return data;
  } catch (error) {
    console.error('AI plan type detection error:', error);
    throw error;
  }
}

/**
 * Get comprehensive AI analysis (field mapping + plan type detection)
 */
export async function getEnhancedExtractionAnalysis(
  extracted_headers: string[],
  table_sample_data: string[][],
  document_context: Record<string, any>,
  carrier_id?: string,
  extracted_carrier?: string,
  token?: string
): Promise<EnhancedExtractionAnalysisResponse> {
  try {
    console.log('🚀 Enhanced AI Analysis: Requesting comprehensive analysis');

    const response = await fetch(`${API_BASE_URL}/api/ai/enhanced-extraction-analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      credentials: 'include',
      body: JSON.stringify({
        extracted_headers,
        table_sample_data,
        document_context,
        carrier_id,
        extracted_carrier
      })
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('401: Authentication required. Please log in again.');
      }
      const error = await response.json().catch(() => ({ detail: 'Enhanced AI analysis failed' }));
      throw new Error(error.detail || `Enhanced AI analysis failed (${response.status})`);
    }

    const data = await response.json();
    console.log('✅ Enhanced AI Analysis: Complete', {
      field_mapping_success: data.field_mapping?.success,
      plan_detection_success: data.plan_type_detection?.success,
      overall_confidence: data.overall_confidence
    });

    return data;
  } catch (error) {
    console.error('Enhanced AI analysis error:', error);
    throw error;
  }
}

/**
 * Save user corrections to improve AI learning
 */
export async function saveUserCorrections(
  upload_id: string,
  carrier_id: string | null,
  original_mappings: Record<string, string>,
  corrected_mappings: Record<string, string>,
  headers: string[],
  token: string
): Promise<{ success: boolean; message: string }> {
  try {
    console.log('📚 Learning: Saving user corrections', {
      upload_id,
      corrections_count: Object.keys(corrected_mappings).length
    });

    const response = await fetch(`${API_BASE_URL}/api/ai/save-user-corrections`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include',
      body: JSON.stringify({
        upload_id,
        carrier_id,
        original_mappings,
        corrected_mappings,
        headers
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to save corrections');
    }

    const data = await response.json();
    console.log('✅ Learning: User corrections saved successfully');

    return data;
  } catch (error) {
    console.error('Failed to save user corrections:', error);
    throw error;
  }
}

/**
 * Get AI services status
 */
export async function getAIServicesStatus(token: string): Promise<{
  success: boolean;
  services: {
    field_mapping: Record<string, any>;
    plan_type_detection: Record<string, any>;
  };
  overall_status: string;
  ai_intelligence_enabled: boolean;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/ai/service-status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get service status');
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to get AI services status:', error);
    throw error;
  }
}

/**
 * Helper function to format confidence as percentage
 */
export function formatConfidence(confidence: number): string {
  return `${(confidence * 100).toFixed(0)}%`;
}

/**
 * Helper function to get confidence color
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-600';
  if (confidence >= 0.5) return 'text-yellow-600';
  return 'text-red-600';
}

/**
 * Helper function to get confidence badge color
 */
export function getConfidenceBadgeColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400';
  if (confidence >= 0.5) return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300';
  return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
}

/**
 * Helper function to determine if mapping requires review
 */
export function requiresReview(confidence: number): boolean {
  return confidence < 0.7;
}

/**
 * Helper function to group mappings by confidence level
 */
export function groupMappingsByConfidence(mappings: FieldMapping[]): {
  high: FieldMapping[];
  medium: FieldMapping[];
  low: FieldMapping[];
} {
  return {
    high: mappings.filter(m => m.confidence >= 0.8),
    medium: mappings.filter(m => m.confidence >= 0.5 && m.confidence < 0.8),
    low: mappings.filter(m => m.confidence < 0.5)
  };
}

/**
 * Helper function to format plan type detection summary
 */
export function formatPlanTypeSummary(detections: PlanTypeDetection[]): string {
  if (detections.length === 0) return 'No plan types detected';
  if (detections.length === 1) return detections[0].plan_type;
  return `${detections.length} plan types: ${detections.map(d => d.plan_type).join(', ')}`;
}

export default {
  getAIFieldMappings,
  getAIPlanTypeDetection,
  getEnhancedExtractionAnalysis,
  saveUserCorrections,
  getAIServicesStatus,
  formatConfidence,
  getConfidenceColor,
  getConfidenceBadgeColor,
  requiresReview,
  groupMappingsByConfidence,
  formatPlanTypeSummary
};

