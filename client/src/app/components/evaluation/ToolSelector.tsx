'use client';

import { cn } from '@/lib/utils';

export const ALL_TOOLS = [
  { id: 'pymupdf',       label: 'PyMuPDF',        description: 'Rule-based PDF text extraction' },
  { id: 'docling',       label: 'Docling',         description: 'Microsoft Table Transformer + OCR' },
  { id: 'aws_textract',  label: 'AWS Textract',    description: 'Amazon Textract AnalyzeDocument (TABLES)' },
  { id: 'google_docai',  label: 'Google DocAI',    description: 'Google Document AI Form Parser' },
  { id: 'gpt5',          label: 'GPT-5 Vision',    description: 'OpenAI multimodal extraction' },
  { id: 'claude_sonnet', label: 'Claude Sonnet',   description: 'Anthropic claude-sonnet-4' },
  { id: 'mistral',       label: 'Mistral AI',      description: 'Mistral OCR + Pixtral Large' },
] as const;

export type ToolId = typeof ALL_TOOLS[number]['id'];

/**
 * Initial tool selection on the batch evaluation page.
 * Keep aligned with server DEFAULT_EXTRACTION_TOOL (default pymupdf) for local testing.
 * Revert to e.g. ['claude_sonnet'] or ALL_TOOLS.map(t => t.id) when switching back.
 */
export const DEFAULT_SELECTED_TOOLS: ToolId[] = ['pymupdf'];

interface Props {
  selected: ToolId[];
  onChange: (tools: ToolId[]) => void;
}

export default function ToolSelector({ selected, onChange }: Props) {
  const toggleAll = () => {
    if (selected.length === ALL_TOOLS.length) onChange([]);
    else onChange(ALL_TOOLS.map(t => t.id));
  };

  const toggle = (id: ToolId) => {
    if (selected.includes(id)) onChange(selected.filter(t => t !== id));
    else onChange([...selected, id]);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Extraction Tools</h3>
        <button onClick={toggleAll} className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 transition-colors">
          {selected.length === ALL_TOOLS.length ? 'Deselect all' : 'Select all'}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {ALL_TOOLS.map(tool => {
          const checked = selected.includes(tool.id);
          return (
            <label
              key={tool.id}
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                checked
                  ? 'border-indigo-300 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-900/20'
                  : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50'
              )}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggle(tool.id)}
                className="mt-0.5 accent-indigo-600"
              />
              <div>
                <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{tool.label}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{tool.description}</div>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
