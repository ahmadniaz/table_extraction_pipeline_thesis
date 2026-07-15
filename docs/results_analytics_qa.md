# Results Analytics — engineering QA (self-audit)

Internal checklist. **Not** shown in the product UI. Last pass: 2026-04-25 (code + `npm run build`).

## Checklist (each item: **PASS** / **FAIL**)

| Item | Status | Notes |
|------|--------|--------|
| Data mapping for metrics and fields | **PASS** | `GET /api/analytics/dataset` matches `ExtractionTableRow` / `buildDataset.mergeRows` / `ALL_EVAL_TOOLS` order aligned with server `ALL_TOOLS`. |
| Missing / undefined metrics | **PASS** | Table-level: `null` in score omitted from inner means; `0.0` kept. Document×tool: `metricValueForRow` + policies in `aggregationPolicy.ts`. |
| Every chart: correct data, axes, units | **PASS** | Reviewed: accuracy charts use policy; cost/time scatters use means of $/pg and `processing_time_ms`; structure plots map GriTS-Top/Con and TEDS/F1 as documented; line chart uses mean per (tool×tier) along `TIER_ORDER`. |
| Filters keep charts and table in sync | **PASS** | Single `filteredDocToolRows` from `filterDocumentToolRows` feeds page, visualizations, CSV, summary. `aggregateMode` is **display-only** for the table (see `types.ts`). |
| Tool colors consistent | **PASS** | `chartColorForTool` / `TOOL_CHART_COLOR_HEX` used for tool-colored series. |
| PNG export (3×, filename, captured DOM) | **PASS** | `CHART_EXPORT_SCALE = 3`, `exportFileName` per card, `onclone` overflow + white bg, `data-export-ignore` on controls. **Manual:** spot-check a PNG in light/dark. |
| Analytics vs “thesis numbers” in prose | **N/A** | Thesis PDF not in repo. **Manual:** recompute any quoted aggregate F1 / ranking from the same filter defaults as the paper. |
| Empty / error / loading states | **PASS** (post-fix) | Empty filter slice: banner + per-chart `ChartDataEmpty`; API error/loading in `page.tsx`. |
| Code structure & types | **PASS** | `tier.ts` for canonical tiers; `chartUtils` + `buildDataset` + `types` cover shapes. Further split of `AnalyticsVisualizations` optional. |

## Issues found and fixes applied (this pass)

1. **Tier keys:** Raw DB tier strings that were not in `{low, medium, high, unconfirmed}` could miss tier buckets. **Fix:** `normalizeComplexityTier` in `client/src/lib/analytics/tier.ts`, applied in `mergeRows` and in chart bucketing / heatmap filters.
2. **Empty after aggressive filters:** Recharts and blank canvases. **Fix:** `ChartDataEmpty` + non-empty guards for rank, box, scatters, cost×commercial-only bars; top banner when `rows.length === 0`.
3. **Structure scatter:** Inlined recompute in JSX replaced with `useMemo` for GriTS/TEDS point lists; axis labels clarify structure vs content.
4. **Cost “commercial only” filter:** `costTierData` can be `[]` — **Fix:** message when no commercial tool rows to plot.
5. **Matrix table:** Empty and search-miss now single-branch rows (no double empty row).

## Known limitations (acceptable / manual)

- **Thesis text:** You must ensure chapter numbers match a chosen filter + policy + time window; the app does not read LaTeX.
- **html2canvas:** Browser-specific quirks (fonts, CORS) — if a PNG is wrong, try SVG export or copy.
- **“Failures” filter:** Counts `reliability === 'complete_failure'`, which includes runs where any table had `is_transient_failure` (see `pickReliability`).
- **Batch QA:** This document is a static audit; re-run `npm run build` and spot-check the UI when changing data or server schema.

## PASS criteria for “thesis ready”

All checklist rows above **PASS** or **N/A** with a manual follow-up; build green; and you have personally verified 2–3 exported PNGs and one CSV against SQL or the API.
