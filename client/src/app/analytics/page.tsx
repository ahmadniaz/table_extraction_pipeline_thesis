'use client';

import { AlertCircle, Loader2 } from 'lucide-react';
import { useAnalyticsData } from '@/hooks/useAnalyticsData';
import { ThesisFiguresView } from '@/app/components/thesisFigures/ThesisFiguresView';

/**
 * Minimal thesis figure generator: full (document×tool) dataset, no dashboard filters.
 * See repository `analyticsPage.md` for the chart list and copy.
 */
export default function ThesisFiguresPage() {
  const { allDocToolRows, documents, loading, error } = useAnalyticsData();

  if (error) {
    return (
      <div className="min-h-full bg-white px-4 py-12">
        <div className="mx-auto flex max-w-2xl items-center gap-3 rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center gap-2 text-slate-500">
        <Loader2 className="h-6 w-6 animate-spin" />
        Loading evaluation dataset…
      </div>
    );
  }

  return (
    <div className="min-h-full bg-white text-slate-900 [color-scheme:light]">
      <div className="mx-auto max-w-5xl space-y-10 px-4 py-10 sm:px-6">
        <header className="space-y-2 border-b border-slate-200 pb-6">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Thesis Figures</h1>
          <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
            Download publication-ready charts for the Results chapter (PNG, 3×). Figures use the full evaluation
            dataset: one row per (document×tool) with the same strict aggregation as elsewhere in the project.
          </p>
        </header>
        <ThesisFiguresView rows={allDocToolRows} docCount={documents.length} />
      </div>
    </div>
  );
}
