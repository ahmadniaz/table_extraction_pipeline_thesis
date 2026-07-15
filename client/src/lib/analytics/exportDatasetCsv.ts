import { toolLabel } from '@/lib/analytics/chartUtils';
import type { DocumentToolAggregate } from '@/lib/analytics/types';

/** Step 5 — export current analytics slice (document × tool) as CSV. */
export function downloadFilteredDocumentToolCsv(rows: DocumentToolAggregate[], filename = 'results-analytics-filtered.csv') {
  const header = [
    'document_id',
    'filename',
    'carrier',
    'complexity_tier',
    'tool',
    'tool_label',
    'generation',
    'precision',
    'recall',
    'f1_score',
    'teds_score',
    'grits_top',
    'grits_con',
    'grits_loc',
    'processing_time_ms',
    'cost_usd_total',
    'cost_per_page',
    'reliability',
  ];
  const lines = [header.join(',')];
  for (const r of rows) {
    const esc = (v: string | number | null | undefined) => {
      if (v == null) return '';
      const s = String(v);
      if (s.includes(',') || s.includes('"') || s.includes('\n')) return `"${s.replace(/"/g, '""')}"`;
      return s;
    };
    lines.push(
      [
        r.document_id,
        r.filename,
        r.carrier,
        r.complexity_tier,
        r.tool_name,
        toolLabel(r.tool_name),
        r.generation,
        r.precision ?? '',
        r.recall ?? '',
        r.f1_score ?? '',
        r.teds_score ?? '',
        r.grits_top ?? '',
        r.grits_con ?? '',
        r.grits_loc ?? '',
        r.processing_time_ms,
        r.cost_usd_total,
        r.cost_per_page ?? '',
        r.reliability,
      ]
        .map(esc)
        .join(',')
    );
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
