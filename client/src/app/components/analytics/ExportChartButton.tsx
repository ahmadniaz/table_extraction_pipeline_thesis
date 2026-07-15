'use client';

import { useState, type RefObject } from 'react';
import { Copy, Download, FileImage } from 'lucide-react';
import toast from 'react-hot-toast';
import { copyChartPngToClipboard, downloadChartPng, downloadChartSvgIfPresent } from '@/lib/analytics/exportChartImage';
import { cn } from '@/lib/utils';

type Props = {
  targetRef: RefObject<HTMLElement | null>;
  /** Filename stem without extension, e.g. `cost-vs-f1` */
  fileBase: string;
  className?: string;
  /** @default true */
  showSvg?: boolean;
  /** @default true */
  showCopy?: boolean;
};

const btn =
  'flex items-center gap-1 text-xs text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white';

/**
 * PNG (required), optional SVG and copy — buttons are excluded from PNG via `data-export-ignore` on the parent in ChartCard.
 */
export function ExportChartButton({ targetRef, fileBase, className, showSvg = true, showCopy = true }: Props) {
  const [pending, setPending] = useState(false);

  const run = async (fn: () => Promise<void> | void) => {
    setPending(true);
    try {
      await fn();
    } finally {
      setPending(false);
    }
  };

  return (
    <div className={cn('flex flex-wrap items-center justify-end gap-2', className)} data-export-ignore>
      <button
        type="button"
        title="High-resolution PNG (3×) for thesis"
        className={btn}
        disabled={pending}
        onClick={() =>
          void run(async () => {
            try {
              await downloadChartPng(targetRef.current, fileBase);
              toast.success('PNG downloaded');
            } catch (e) {
              toast.error(e instanceof Error ? e.message : 'PNG export failed');
            }
          })
        }
      >
        <Download className="h-3.5 w-3.5" />
        PNG
      </button>
      {showSvg ? (
        <button
          type="button"
          title="Vector SVG of full figure (title, legend, chart)"
          className={btn}
          disabled={pending}
          onClick={() => {
            const ok = downloadChartSvgIfPresent(targetRef.current, fileBase);
            if (ok) toast.success('SVG downloaded');
            else toast.error('No SVG in this view (use PNG)');
          }}
        >
          <FileImage className="h-3.5 w-3.5" />
          SVG
        </button>
      ) : null}
      {showCopy ? (
        <button
          type="button"
          title="Copy figure as image"
          className={btn}
          disabled={pending}
          onClick={() =>
            void run(async () => {
              const ok = await copyChartPngToClipboard(targetRef.current);
              if (ok) toast.success('Image copied to clipboard');
              else toast.error('Copy not supported in this browser');
            })
          }
        >
          <Copy className="h-3.5 w-3.5" />
          Copy
        </button>
      ) : null}
    </div>
  );
}
