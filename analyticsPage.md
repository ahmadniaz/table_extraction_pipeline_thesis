You previously built a broad Results Analytics page, but it is too complex for thesis use. I now want you to simplify it completely and turn it into a thesis-figure generator aligned exactly with my Results and Discussion chapters.

Your job is not to build a generic analytics dashboard. Your job is to produce only the charts that are genuinely necessary for the thesis, with simple controls and direct PNG export so I can place the figures into Chapter 4.

Core instruction
Read the project’s real evaluation data and rework the analytics page into a minimal, thesis-oriented chart page.

The page should:

be simple

be easy to understand at a glance

contain only the charts needed by the thesis

avoid exploratory dashboard complexity

allow direct download of each chart as PNG

use publication-friendly titles and labels

not include unnecessary charts, filters, tabs, or cards

Do not assume extra needs beyond what is supported by the thesis text.

Thesis alignment you must follow
The thesis Results and Discussion chapters focus on these empirical needs:

Aggregate ranking across tools

Performance across LOW / MEDIUM / HIGH tiers

Performance degradation as complexity increases

Difference between structural quality and content quality

Cost-effectiveness

Latency / throughput trade-offs

Failure and partial-extraction behavior

The page should therefore only generate charts that support those exact needs.

Remove dashboard complexity
Please simplify aggressively.

Remove or do not include:
per-document explorer table

large multi-filter control panels

metric heatmap explorer

advanced aggregate mode controls

too many toggles

duplicate charts that show the same story

charts that are interesting technically but not needed in the thesis

“analytics summary cards” unless they are extremely minimal

unnecessary metric switchers on every chart

This should feel like a figure preparation page, not a BI dashboard.

Required charts only
Build exactly these charts.

Chart 1 — Aggregate F1 by Tool
Purpose: support the aggregate ranking in the Results chapter and the cross-generational ordering discussed in the Discussion chapter.

Chart type: horizontal bar chart

Configuration:

Y-axis: tool

X-axis: aggregate F1

sort descending by F1

show exact value labels on bars

title: Aggregate F1 Score by Tool

subtitle optional: Mean F1 across all 50 commission statements

include all 7 tools

Styling:

consistent tool colors

no metric selector

this chart is F1 only

Why this chart exists: this is the clearest visual for the overall ranking, which the thesis repeatedly references.

Chart 2 — F1 by Tool and Complexity Tier
Purpose: support the per-tier LOW / MEDIUM / HIGH results section.

Chart type: grouped bar chart

Configuration:

X-axis: tool

grouped bars: LOW, MEDIUM, HIGH

Y-axis: F1

show exact values or tooltip values

title: F1 Score by Tool Across Complexity Tiers

legend order: LOW, MEDIUM, HIGH

tier order must always be LOW → MEDIUM → HIGH

Styling:

use fixed tier colors

keep tool labels readable

no stacked mode

no metric selector

Why this chart exists: it visually replaces the need to mentally compare Tables 4.3, 4.4, and 4.5 for F1.

Chart 3 — F1 Degradation Across Complexity
Purpose: support the discussion of smooth versus steep degradation across tiers.

Chart type: line chart

Configuration:

X-axis: LOW, MEDIUM, HIGH

Y-axis: F1

one line per tool

show point markers

title: Performance Degradation Across Complexity Tiers

subtitle optional: Mean F1 by tool from LOW to HIGH complexity

Interaction:

allow a very simple legend click to hide/show tools

default view should show all tools

no other filters required

Why this chart exists: this directly supports the argument that Textract degrades smoothly, Claude remains stable, and GPT-5 / Docling / Google DocAI decline more sharply.

Chart 4 — Structural vs Content Accuracy by Tool
Purpose: support the discussion that some tools reconstruct structure better than they recover content, especially Docling, and that some tools show topology/content asymmetry.

Chart type: grouped bar chart

Configuration:

X-axis: tool

two bars per tool:

GriTS-Top

GriTS-Con

values should be aggregate values across all documents

title: Structural vs Content Accuracy by Tool

subtitle optional: Aggregate GriTS-Top and GriTS-Con scores

Important:

this should NOT be a scatter plot in the simplified version

grouped bars are easier to read in a thesis context

exact values in tooltip, optional labels on bars

Why this chart exists: it directly supports the Discussion chapter’s repeated emphasis on the topology-content gap, especially for Docling and GPT-5 at higher complexity.

Chart 5 — Cost vs F1 Trade-off
Purpose: support the cost-effectiveness discussion in RQ3.

Chart type: scatter plot

Configuration:

X-axis: cost per page (USD)

Y-axis: aggregate F1

one point per tool

label each point with tool name

title: Cost–Accuracy Trade-off

subtitle optional: Aggregate F1 versus per-page cost

Important handling:

include only commercial tools by default:

Claude Sonnet

Mistral AI

GPT-5

AWS Textract

Google DocAI

add one simple checkbox:

Include open-source tools at zero cost

if enabled, show Docling and PyMuPDF at cost = 0

Why this chart exists: this is the best figure for supporting the claim that Mistral is the strongest cost-efficiency option and GPT-5 is hard to justify on cost grounds.

Chart 6 — Runtime vs F1 Trade-off
Purpose: support the latency and throughput discussion.

Chart type: scatter plot

Configuration:

X-axis: average processing time per document (ms)

Y-axis: aggregate F1

one point per tool

label each point with tool name

title: Latency–Accuracy Trade-off

subtitle optional: Aggregate F1 versus average processing time per document

Interaction:

add one simple toggle:

Log scale for runtime

default should be normal scale

Why this chart exists: this directly visualizes GPT-5 as slowest, PyMuPDF fastest, and the commercial speed/accuracy placement of Textract, Google DocAI, Claude, and Mistral.

Chart 7 — Failure and Partial-Extraction Cases by Tool
Purpose: support the Results section on missing F1 rows and the Discussion of structural failures and partial extractions.

Chart type: stacked bar chart

Configuration:

X-axis: tool

stacks:

Successful / scoreable

Complete structural failure

Partial extraction with undefined F1

Y-axis: count of document-tool rows

title: Failure and Partial-Extraction Cases by Tool

Data logic:

use the same classification logic already defined in the project

ensure:

Docling complete failures are counted correctly

PyMuPDF complete failures are counted correctly

Google DocAI partial-extraction cases are counted correctly

tooltip should show category counts

labels optional if clean

Why this chart exists: this is necessary because the thesis explicitly quantifies 19 missing F1 rows and separates complete failures from partial extraction cases.

Optional chart: only if clean and easy
Only include the following if it is simple and visually clean. If it makes the page cluttered, do not include it.

Optional Chart 8 — Cost by Tier for Commercial Tools
Chart type: grouped bar chart

Configuration:

X-axis: tool

grouped bars: LOW, MEDIUM, HIGH

Y-axis: cost per page

commercial tools only

title: Per-Page Cost by Tool and Complexity Tier

Only include this if the chart is readable and truly useful. If not, omit it and rely on the table in the thesis.

Filters: keep only what is necessary
The simplified page should have very few controls.

Allowed controls:
Include open-source tools at zero cost checkbox for the cost scatter

Log scale for runtime toggle for runtime scatter

legend click hide/show for multi-series charts

download PNG button for each chart

Do not include:
carrier filter

document filter

generation filter

aggregate mode selector

failure status filters

runtime range filters

cost range filters

metric dropdowns

raw table view

This is for final thesis figures, not exploratory analysis.

Export requirements
Every chart must have a visible button:

Download PNG

Requirements:

export that single chart only

high resolution suitable for thesis insertion

minimum 3x scale if using html2canvas or similar

include title, axis labels, legend, and plotted values

use descriptive filenames:

aggregate-f1-by-tool.png

f1-by-tool-and-tier.png

f1-degradation-by-tier.png

grits-top-vs-grits-con-by-tool.png

cost-vs-f1.png

runtime-vs-f1.png

failure-and-partial-extraction-by-tool.png

Visual style
Use a restrained academic style:

white background

dark text

muted gridlines

no heavy shadows

no decorative cards

no unnecessary animation

clean typography

chart titles large and readable

export-friendly color contrast

Color rules
Keep colors consistent across charts.

Claude Sonnet: consistent color everywhere

Mistral AI: consistent color everywhere

GPT-5: consistent color everywhere

AWS Textract: consistent color everywhere

Google DocAI: consistent color everywhere

Docling: consistent color everywhere

PyMuPDF: consistent color everywhere

For tier-colored grouped charts, use:

LOW = one fixed color

MEDIUM = one fixed color

HIGH = one fixed color

For Chart 4:

GriTS-Top = one fixed color

GriTS-Con = one fixed color

For Chart 7:

Successful = neutral/positive

Complete failure = strong warning color

Partial extraction = distinct secondary warning color

Data accuracy requirements
Do not alter the established thesis aggregation rules.

Use the same dataset and methodology already used in the project:

aggregate values must match the thesis numbers

per-tier values must match the thesis numbers

failure counts must match the thesis numbers

keep the distinction between:

valid 0 values

null / undefined F1

complete structural failure

partial extraction

If any chart currently uses inconsistent logic, fix it.

Page layout
Create one very simple page:

page title: Thesis Figures

short helper text: Download publication-ready charts for the Results chapter

charts stacked vertically in a clean order:

Aggregate F1 by Tool

F1 by Tool and Complexity Tier

F1 Degradation Across Complexity

Structural vs Content Accuracy by Tool

Cost–Accuracy Trade-off

Latency–Accuracy Trade-off

Failure and Partial-Extraction Cases by Tool

optional cost-by-tier chart only if still clean

Do not create tabs unless absolutely necessary. Vertical flow is preferred.

Final cleanup task
After implementing, review the page and remove anything that still feels like a dashboard rather than a thesis figure page.

The result should feel:

simpler

focused

publication-oriented

directly aligned to Chapters 4 and 5

If a chart does not clearly support a specific paragraph or subsection in the thesis, remove it.

Exact chapter-to-chart mapping
Use this mapping as your ground truth:

Aggregate Quantitative Results → Chart 1

Per-Tier Results → Chart 2 and Chart 3

Structural/content differences discussed across Results + Discussion → Chart 4

Results for Cost and Processing Time → Chart 5 and Chart 6

Observed Failure and Partial-Extraction Cases → Chart 7

optional Per-Tier Cost Results → Optional Chart 8 only if visually worthwhile

Final verification
Before finishing, verify:

the page is much simpler than before

every remaining chart serves a clear thesis purpose

PNG export works for every chart

chart values match the thesis tables

no unnecessary filters or complexity remain

Do not leave behind old exploratory dashboard elements unless they are completely hidden from the main thesis figure page.