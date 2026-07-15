import type { ToolGeneration } from '@/lib/analytics/types';

/**
 * Consistent, thesis-friendly colors for Results Analytics charts.
 * Rule-based / CV / LLM families (muted, publication-safe).
 * Use the same map across all charts in Step 4+.
 */

export const TOOL_CHART_COLOR_HEX: Record<string, string> = {
  pymupdf: '#64748b',
  aws_textract: '#0e7490',
  google_docai: '#0369a1',
  docling: '#0f766e',
  gpt5: '#6d28d9',
  claude_sonnet: '#7c3aed',
  mistral: '#8b5cf6',
} as const;

const ORDER = [
  'pymupdf',
  'aws_textract',
  'google_docai',
  'docling',
  'gpt5',
  'claude_sonnet',
  'mistral',
] as const;

/** Stable ordered palette for “one color per series” fallbacks. */
export const CHART_COLOR_SEQUENCE = ORDER.map(id => TOOL_CHART_COLOR_HEX[id]);

export function chartColorForTool(toolId: string): string {
  return TOOL_CHART_COLOR_HEX[toolId] ?? '#475569';
}

/** LOW / MEDIUM / HIGH tier lines or bars (consistent across charts). */
export const TIER_COLOR_HEX: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#ef4444',
} as const;

export function chartColorForTier(tier: string): string {
  const k = tier.toLowerCase();
  return TIER_COLOR_HEX[k] ?? '#94a3b8';
}

/** Chart 4: GriTS-Top (structure) vs GriTS-Con (content), grouped — consistent across the thesis. */
export const GRTS_TOP_GROUP_COLOR = '#1e3a5f';
export const GRTS_CON_GROUP_COLOR = '#9a3412';

/** Chart 7: three-stack reliability (academic, export-safe contrast). */
export const THESIS_STACK_SUCCESS = '#16a34a';
export const THESIS_STACK_FAIL = '#dc2626';
export const THESIS_STACK_PARTIAL = '#d97706';

export const TOOL_ID_TO_GENERATION: Record<string, ToolGeneration> = {
  pymupdf: 'rule',
  aws_textract: 'cv',
  google_docai: 'cv',
  docling: 'cv',
  gpt5: 'llm',
  claude_sonnet: 'llm',
  mistral: 'llm',
};

/** No API cost: local / open-weights on-prem style — used for “commercial” filters and cost× charts. */
export const OPEN_SOURCE_TOOL_IDS: ReadonlySet<string> = new Set(['pymupdf', 'docling']);
