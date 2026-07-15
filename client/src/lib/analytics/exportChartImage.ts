/**
 * PNG / SVG / clipboard export for chart cards.
 * PNG: html2canvas (3×) with `onclone` inlining. Modern CSS (oklch/color()) is normalized to
 * sRGB in `syncComputedStylesOntoClone` so the rasterizer never parses unsupported color syntax.
 * SVG: full figure (title, legend, chart) via `<foreignObject>` + inlined XHTML, not the plot SVG
 * alone — the latter omits HTML legend/titles in Recharts.
 */
import html2canvas from 'html2canvas';

const FALLBACK_SRGB = 'rgb(100, 116, 139)'; // slate-500
const FALLBACK_BOX_SHADOW = '0 1px 3px 0 rgba(15, 23, 42, 0.12)';

/** @default 3 — spec asks ≥2x; 3x matches typical thesis figure DPI scaling. */
export const CHART_EXPORT_SCALE = 3;

const MODERN_COLOR_SYNTAX = /oklch|lch\(|lab\(|color\(/i;

function containsModernColorSyntax(value: string): boolean {
  return MODERN_COLOR_SYNTAX.test(value);
}

/**
 * Resolves a single computed CSS value that may be `oklch()` / `color()` to what the engine exposes
 * as sRGB, using a same-property probe. Used for HTML elements during clone sync.
 */
function resolveStylePropertyToSrgb(name: string, value: string, priority: string): string {
  if (!value || !containsModernColorSyntax(value)) return value;
  const probe = document.createElement('div');
  probe.style.setProperty('position', 'fixed', 'important');
  probe.style.setProperty('left', '-9999px', 'important');
  probe.style.setProperty('top', '0', 'important');
  probe.style.setProperty('visibility', 'hidden', 'important');
  document.body.appendChild(probe);
  try {
    probe.style.setProperty(name, value, priority);
    const out = getComputedStyle(probe).getPropertyValue(name);
    if (out && !containsModernColorSyntax(out)) return out;
  } catch {
    /* fall through */
  } finally {
    document.body.removeChild(probe);
  }
  if (name === 'box-shadow') return FALLBACK_BOX_SHADOW;
  if (name === 'text-shadow') return '0 0.5px 0 rgba(15, 23, 42, 0.15)';
  if (name === 'filter' || name === 'backdrop-filter') return 'none';
  if (name === 'background-image') return 'none';
  return FALLBACK_SRGB;
}

/**
 * `color` / `fill` for SVG text: resolve via a probe when `getComputedStyle` still returns
 * modern color syntax.
 */
function resolveCssColorString(value: string): string {
  if (!value || !containsModernColorSyntax(value)) return value;
  const probe = document.createElement('div');
  document.body.appendChild(probe);
  try {
    probe.style.color = value;
    const out = getComputedStyle(probe).color;
    if (out && !containsModernColorSyntax(out)) return out;
  } catch {
    /* ignore */
  } finally {
    document.body.removeChild(probe);
  }
  return FALLBACK_SRGB;
}

/** If the browser still exposes an oklch/lab value on SVG paint, resolve to rgb for portable SVG. */
function resolveSvgPaintToRgb(value: string, attr: 'fill' | 'stroke'): string {
  if (!value || value === 'none' || /^(url\(|context-|currentColor)/i.test(value)) return value;
  if (!containsModernColorSyntax(value)) return value;
  if (typeof document === 'undefined') return value;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  el.setAttribute('r', '1');
  el.setAttribute(attr, value);
  svg.appendChild(el);
  svg.setAttribute('style', 'position:absolute;left:-9999px;width:0;height:0;overflow:hidden;pointer-events:none;');
  document.body.appendChild(svg);
  try {
    const cs = getComputedStyle(el);
    const out = attr === 'fill' ? cs.fill : cs.stroke;
    if (out && out !== 'none' && !containsModernColorSyntax(out)) return out;
  } finally {
    document.body.removeChild(svg);
  }
  return FALLBACK_SRGB;
}

/**
 * Copy resolved computed styles from the live `source` tree onto `cloned` (html2canvas's clone)
 * and rewrite any color-like value that still uses `oklch`/`color()` so the rasterizer never sees
 * unsupported syntax.
 */
function syncComputedStylesOntoClone(sourceRoot: HTMLElement, clonedRoot: HTMLElement) {
  const sourceNodes: Element[] = [sourceRoot, ...sourceRoot.querySelectorAll('*')];
  const cloneNodes: Element[] = [clonedRoot, ...clonedRoot.querySelectorAll('*')];
  if (sourceNodes.length !== cloneNodes.length) {
    return;
  }
  for (let i = 0; i < sourceNodes.length; i++) {
    const src = sourceNodes[i]!;
    const dst = cloneNodes[i]!;
    const cs = window.getComputedStyle(src);
    if (dst instanceof HTMLElement) {
      for (let j = 0; j < cs.length; j++) {
        const name = cs[j];
        if (!name) continue;
        const priority = cs.getPropertyPriority(name);
        let val = cs.getPropertyValue(name);
        if (!val) continue;
        if (containsModernColorSyntax(val)) {
          val = resolveStylePropertyToSrgb(name, val, priority);
        }
        dst.style.setProperty(name, val, priority);
      }
    } else if (dst instanceof SVGElement && src instanceof SVGElement) {
      try {
        const fill = resolveSvgPaintToRgb(cs.fill || 'none', 'fill');
        const stroke = resolveSvgPaintToRgb(cs.stroke || 'none', 'stroke');
        dst.setAttribute('fill', fill);
        dst.setAttribute('stroke', stroke);
        if (cs.color) dst.setAttribute('color', resolveCssColorString(cs.color));
      } catch {
        /* ignore */
      }
    }
  }
}

/**
 * Inlines the same way as the PNG path (for a detached clone) — used for SVG `foreignObject` export.
 */
function inlineStylesForExportClone(sourceRoot: HTMLElement, clonedRoot: HTMLElement) {
  syncComputedStylesOntoClone(sourceRoot, clonedRoot);
  clonedRoot.className = '';
  clonedRoot.querySelectorAll<Element>('*').forEach(node => {
    node.removeAttribute('class');
  });
  clonedRoot.querySelectorAll('[data-export-ignore]').forEach(n => {
    if (n instanceof HTMLElement) n.style.setProperty('display', 'none', 'important');
  });
}

const SVG_NS = 'http://www.w3.org/2000/svg';
const XHTML_NS = 'http://www.w3.org/1999/xhtml';

/**
 * Exports the full capture `el` (title, subtitle, legend, chart) as a standalone SVG using
 * `foreignObject` + XHTML, because Recharts puts legend and headings outside the plot &lt;svg&gt;.
 */
function downloadCaptureAsForeignObjectSvg(el: HTMLElement, fileBase: string): boolean {
  const clone = el.cloneNode(true) as HTMLElement;
  inlineStylesForExportClone(el, clone);

  const rect = el.getBoundingClientRect();
  const w = Math.max(1, Math.round(rect.width) || el.offsetWidth);
  const h = Math.max(1, Math.round(Math.max(rect.height, el.scrollHeight, el.offsetHeight)));

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('xmlns', SVG_NS);
  svg.setAttribute('width', String(w));
  svg.setAttribute('height', String(h));
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);

  const fo = document.createElementNS(SVG_NS, 'foreignObject');
  fo.setAttribute('x', '0');
  fo.setAttribute('y', '0');
  fo.setAttribute('width', String(w));
  fo.setAttribute('height', String(h));

  const wrap = document.createElementNS(XHTML_NS, 'div');
  wrap.setAttribute('xmlns', XHTML_NS);
  wrap.style.width = `${w}px`;
  wrap.style.minHeight = `${h}px`;
  wrap.style.boxSizing = 'border-box';
  wrap.style.backgroundColor = '#ffffff';
  wrap.appendChild(clone);
  fo.appendChild(wrap);
  svg.appendChild(fo);

  const safe = fileBase.replace(/[^a-zA-Z0-9-_]+/g, '-').replace(/^-|-$/g, '') || 'chart';
  const str =
    '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(svg) + '\n';
  const blob = new Blob([str], { type: 'image/svg+xml;charset=utf-8' });
  downloadBlob(blob, `${safe}.svg`);
  return true;
}

export function downloadBlob(blob: Blob, filename: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/**
 * Renders a DOM subtree to a PNG. Omits elements under `data-export-ignore` in output (hidden
 * after inlining, not `ignoreElements` — keeps clone/snapshot tree structure aligned).
 */
export async function captureElementToPng(
  el: HTMLElement,
  scale: number = CHART_EXPORT_SCALE
): Promise<HTMLCanvasElement> {
  return html2canvas(el, {
    scale,
    useCORS: true,
    allowTaint: true,
    backgroundColor: '#ffffff',
    logging: false,
    onclone: (_doc, clone) => {
      if (!(clone instanceof HTMLElement)) return;
      syncComputedStylesOntoClone(el, clone);
      clone.className = '';
      clone.querySelectorAll<Element>('*').forEach(node => {
        node.removeAttribute('class');
      });
      clone.querySelectorAll('[data-export-ignore]').forEach(n => {
        if (n instanceof HTMLElement) n.style.setProperty('display', 'none', 'important');
      });
      clone.style.overflow = 'visible';
      clone.style.setProperty('background-color', '#ffffff', 'important');
    },
  });
}

export async function downloadChartPng(el: HTMLElement | null, fileBase: string): Promise<void> {
  if (!el) return;
  const safe = fileBase.replace(/[^a-zA-Z0-9-_]+/g, '-').replace(/^-|-$/g, '') || 'chart';
  const canvas = await captureElementToPng(el);
  const a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = `${safe}.png`;
  a.click();
}

/**
 * Full-figure SVG (title, html legend, axes, plot). Uses `foreignObject` so Recharts’ HTML
 * layers (legend, headings) are included; plot-only &lt;svg&gt; would drop them.
 */
export function downloadChartSvgIfPresent(el: HTMLElement | null, fileBase: string): boolean {
  if (!el) return false;
  return downloadCaptureAsForeignObjectSvg(el, fileBase);
}

export async function copyChartPngToClipboard(el: HTMLElement | null): Promise<boolean> {
  if (!el) return false;
  const canvas = await captureElementToPng(el);
  const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
  if (!blob || !navigator.clipboard?.write) return false;
  try {
    await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
    return true;
  } catch {
    return false;
  }
}
