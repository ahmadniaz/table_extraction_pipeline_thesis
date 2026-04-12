/**
 * Must stay aligned with server `ALL_TOOLS` in `server/app/api/evaluation.py`.
 * Claude is seeded on upload — no Extract button on the per-document page.
 */
export const ALL_EVAL_TOOLS = [
  { id: 'pymupdf', label: 'PyMuPDF', gen: 'Rule-based' },
  { id: 'docling', label: 'Docling', gen: 'Computer Vision' },
  { id: 'aws_textract', label: 'AWS Textract', gen: 'Computer Vision' },
  { id: 'google_docai', label: 'Google DocAI', gen: 'Computer Vision' },
  { id: 'gpt5', label: 'GPT-5 Vision', gen: 'LLM' },
  { id: 'claude_sonnet', label: 'Claude Sonnet', gen: 'LLM' },
  { id: 'mistral', label: 'Mistral AI', gen: 'LLM' },
] as const;

export type EvalToolId = (typeof ALL_EVAL_TOOLS)[number]['id'];

export const CLAUDE_TOOL_ID: EvalToolId = 'claude_sonnet';

export function isExtractableTool(id: string): boolean {
  return id !== CLAUDE_TOOL_ID;
}
