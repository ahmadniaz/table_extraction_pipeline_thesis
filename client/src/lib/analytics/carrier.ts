const STOP = new Set(
  'statement,commission,report,monthly,annual,summary,final,original,finalized,copy,scan,scanned,pdf,doc,docx'.split(',')
);

/** Best-effort carrier from filename: first meaningful token, else “Unknown”. */
export function inferCarrierFromFilename(filename: string): string {
  const base = filename.replace(/\.[^/.]+$/, '');
  const parts = base.split(/[\s_\-/]+/).filter(Boolean);
  for (const p of parts) {
    const t = p.replace(/[^a-zA-Z0-9&]/g, '');
    if (t.length < 2) continue;
    if (STOP.has(t.toLowerCase())) continue;
    if (/^\d/.test(t)) continue;
    return t.length > 1 ? t.charAt(0).toUpperCase() + t.slice(1) : t;
  }
  return 'Unknown';
}
