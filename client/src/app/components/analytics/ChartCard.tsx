'use client';

import { useRef, type ReactNode } from 'react';
import { ExportChartButton } from '@/app/components/analytics/ExportChartButton';
import { cn } from '@/lib/utils';

export type ChartCardProps = {
  title: string;
  subtitle?: string;
  className?: string;
  children?: ReactNode;
  contentMinHeightClassName?: string;
  /**
   * Base filename (no extension) for PNG/SVG/copy, e.g. `aggregate-f1-by-tool`.
   * When set, a capture region includes title, subtitle, and chart body; export controls are excluded.
   */
  exportFileName?: string;
  /** @default true */
  exportShowSvg?: boolean;
  /** @default true */
  exportShowCopy?: boolean;
  /** Simpler border for thesis: no card shadow. */
  thesisStyle?: boolean;
};

/**
 * Single thesis figure: white surface, light border.
 * With `exportFileName`, includes Download PNG / SVG / Copy (see ExportChartButton).
 */
export function ChartCard({
  title,
  subtitle,
  className,
  children,
  contentMinHeightClassName = 'min-h-[220px]',
  exportFileName,
  exportShowSvg = true,
  exportShowCopy = true,
  thesisStyle = false,
}: ChartCardProps) {
  const captureRef = useRef<HTMLDivElement>(null);

  return (
    <div
      className={cn(
        'rounded border bg-white',
        thesisStyle ? 'border-slate-200 shadow-none' : 'border-slate-200/90 shadow-sm dark:border-slate-700 dark:bg-slate-900/40',
        className
      )}
    >
      <div ref={captureRef} className={cn('overflow-visible rounded bg-white', !thesisStyle && 'dark:bg-slate-900/40')}>
        <div
          className={cn(
            'flex items-start justify-between gap-2 border-b px-4 py-3',
            thesisStyle ? 'border-slate-200' : 'border-slate-100 dark:border-slate-700/80'
          )}
        >
          <div className="min-w-0 flex-1">
            <h2
              className={cn(
                'font-semibold text-slate-900',
                thesisStyle ? 'text-xl' : 'text-base tracking-tight dark:text-slate-100'
              )}
            >
              {title}
            </h2>
            {subtitle ? (
              <p
                className={cn(
                  'mt-0.5 text-sm',
                  thesisStyle ? 'text-slate-600' : 'leading-relaxed text-slate-500 dark:text-slate-400'
                )}
              >
                {subtitle}
              </p>
            ) : null}
          </div>
          {exportFileName ? (
            <ExportChartButton
              targetRef={captureRef}
              fileBase={exportFileName}
              showSvg={exportShowSvg}
              showCopy={exportShowCopy}
            />
          ) : null}
        </div>
        <div className={cn('px-4 py-4', contentMinHeightClassName)}>{children}</div>
      </div>
    </div>
  );
}
