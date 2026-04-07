import { cn } from '@/lib/utils';

type Tier = 'low' | 'medium' | 'high';

const CONFIG: Record<Tier, { label: string; className: string }> = {
  low:    { label: 'Low',    className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300' },
  medium: { label: 'Medium', className: 'bg-amber-100  text-amber-800  dark:bg-amber-900/40  dark:text-amber-300'  },
  high:   { label: 'High',   className: 'bg-red-100    text-red-800    dark:bg-red-900/40    dark:text-red-300'    },
};

export default function TierBadge({ tier }: { tier: Tier }) {
  const cfg = CONFIG[tier] ?? CONFIG.medium;
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', cfg.className)}>
      {cfg.label}
    </span>
  );
}
