import type { ScoreMetric } from '@/lib/analytics/types';

export const METRIC_LABEL: Record<ScoreMetric, string> = {
  f1_score: 'F1',
  teds_score: 'TEDS',
  grits_top: 'GriTS-Top',
  grits_con: 'GriTS-Con',
  grits_loc: 'GriTS-Loc',
  precision: 'Precision',
  recall: 'Recall',
};
