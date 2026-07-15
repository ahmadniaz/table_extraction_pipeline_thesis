import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Thesis Figures | PDF Table Extraction Evaluator',
  description: 'Publication-ready figures for the thesis Results chapter: F1, tiers, cost, runtime, and failures.',
};

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
