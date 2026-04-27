# PPTX Generation Instructions

Use `pptxgenjs` (npm package, installed globally). Write complete, self-contained JavaScript that creates a `.pptx` file in the current working directory.

## Setup

```javascript
const pptxgen = require("pptxgenjs");

let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';   // 10" × 5.625" — use this as default
pres.title = 'Presentation Title';

let slide = pres.addSlide();
slide.addText("Hello World!", { x: 0.5, y: 0.5, w: 9, h: 1, fontSize: 36, color: "363636" });

pres.writeFile({ fileName: "output.pptx" });
```

## Layout Dimensions (inches)

- `LAYOUT_16x9`: 10" × 5.625" (default — use this)
- `LAYOUT_16x10`: 10" × 6.25"
- `LAYOUT_4x3`: 10" × 7.5"
- `LAYOUT_WIDE`: 13.3" × 7.5"

---

## Text & Formatting

```javascript
// Basic text
slide.addText("Title Text", {
  x: 0.5, y: 0.5, w: 9, h: 1,
  fontSize: 36, fontFace: "Calibri", color: "1E2761",
  bold: true, align: "center", valign: "middle"
});

// Rich text array (mixed formatting)
slide.addText([
  { text: "Bold ", options: { bold: true } },
  { text: "Italic ", options: { italic: true } },
  { text: "Normal" }
], { x: 0.5, y: 2, w: 9, h: 1 });

// Multi-line text
slide.addText([
  { text: "Line 1", options: { breakLine: true } },
  { text: "Line 2", options: { breakLine: true } },
  { text: "Line 3" }
], { x: 0.5, y: 1, w: 9, h: 2 });

// Align text precisely with shapes — set margin: 0
slide.addText("Title", { x: 0.5, y: 0.3, w: 9, h: 0.6, margin: 0 });
```

## Bullet Lists — NEVER use unicode bullets

```javascript
// ✅ CORRECT
slide.addText([
  { text: "First item", options: { bullet: true, breakLine: true } },
  { text: "Second item", options: { bullet: true, breakLine: true } },
  { text: "Sub-item", options: { bullet: true, indentLevel: 1, breakLine: true } },
  { text: "Numbered", options: { bullet: { type: "number" } } }
], { x: 0.5, y: 0.5, w: 8, h: 3 });

// ❌ WRONG — never do this
slide.addText("• First item", { ... });
```

## Shapes

```javascript
// Rectangle
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0, y: 0, w: 10, h: 0.8,
  fill: { color: "1E2761" }
});

// Rounded rectangle
slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 1, y: 1, w: 3, h: 2,
  fill: { color: "FFFFFF" }, rectRadius: 0.1
});

// Shadow — NEVER encode opacity in hex color
slide.addShape(pres.shapes.RECTANGLE, {
  x: 1, y: 1, w: 3, h: 2, fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.15 }
});

// Line
slide.addShape(pres.shapes.LINE, {
  x: 0.5, y: 2, w: 9, h: 0, line: { color: "CCCCCC", width: 1 }
});
```

## Slide Backgrounds

```javascript
slide.background = { color: "1E2761" };           // Solid color
slide.background = { path: "https://..." };        // Image URL
slide.background = { data: "image/png;base64,..." }; // Base64
```

## Images

```javascript
// From URL
slide.addImage({ path: "https://example.com/image.jpg", x: 5, y: 1, w: 4, h: 3 });

// From file
slide.addImage({ path: "./logo.png", x: 0.5, y: 0.5, w: 1.5, h: 0.5 });

// Circular crop
slide.addImage({ path: "image.png", x: 1, y: 1, w: 2, h: 2, rounding: true });
```

## Tables

```javascript
slide.addTable([
  [{ text: "Header 1", options: { bold: true, fill: { color: "1E2761" }, color: "FFFFFF" } },
   { text: "Header 2", options: { bold: true, fill: { color: "1E2761" }, color: "FFFFFF" } }],
  ["Row 1, Cell 1", "Row 1, Cell 2"],
  ["Row 2, Cell 1", "Row 2, Cell 2"],
], {
  x: 0.5, y: 1.5, w: 9,
  colW: [4.5, 4.5],
  border: { pt: 1, color: "CCCCCC" }
});
```

## Charts

```javascript
// Bar chart
slide.addChart(pres.charts.BAR, [{
  name: "Revenue", labels: ["Q1","Q2","Q3","Q4"], values: [4500,5500,6200,7100]
}], {
  x: 0.5, y: 1, w: 9, h: 4, barDir: "col",
  chartColors: ["0D9488"],
  chartArea: { fill: { color: "FFFFFF" } },
  showValue: true, showLegend: false,
  catAxisLabelColor: "64748B", valAxisLabelColor: "64748B",
  valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
});

// Line chart
slide.addChart(pres.charts.LINE, [{
  name: "Growth", labels: ["Jan","Feb","Mar"], values: [32,35,42]
}], { x: 0.5, y: 1, w: 9, h: 4, lineSize: 2, lineSmooth: true });

// Pie chart
slide.addChart(pres.charts.PIE, [{
  name: "Share", labels: ["A","B","Other"], values: [35,45,20]
}], { x: 2, y: 0.5, w: 6, h: 5, showPercent: true });
```

---

## Design Rules

### Pick a bold color palette for each presentation

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| Midnight Executive | `1E2761` | `CADCFC` | `FFFFFF` |
| Forest & Moss | `2C5F2D` | `97BC62` | `F5F5F5` |
| Coral Energy | `F96167` | `F9E795` | `2F3C7E` |
| Teal Trust | `028090` | `00A896` | `02C39A` |
| Charcoal Minimal | `36454F` | `F2F2F2` | `212121` |

- One color dominates (60-70% visual weight), 1-2 supporting tones, one sharp accent
- Dark/light contrast: dark title + conclusion slides, light content slides ("sandwich")
- Commit to ONE visual motif and repeat it on every slide

### Typography

- Header: 36-44pt bold; Section: 20-24pt bold; Body: 14-16pt; Captions: 10-12pt
- Choose an interesting font pair — don't default to Arial

### Layout ideas per slide

- Two-column (text left, visual right)
- Icon + text rows (icon in colored circle, bold header, description)
- Large stat callouts (60-72pt number with small label)
- Half-bleed background image with content overlay

---

## Critical Rules

- **NEVER use `#` with hex colors** — causes file corruption: `color: "FF0000"` not `color: "#FF0000"`
- **NEVER encode opacity in hex** — use `opacity: 0.15` property, not 8-char hex
- **NEVER reuse option objects** — pptxgenjs mutates them; use a factory function for repeated styles
- **NEVER use unicode bullets** — use `bullet: true`
- **NEVER add accent lines under titles** — hallmark of AI-generated slides; use whitespace instead
- **Don't use `ROUNDED_RECTANGLE` with rectangular accent overlays** — use `RECTANGLE` instead
- **Shadow `offset` must be non-negative** — negative values corrupt the file
- **Each presentation needs a fresh `pptxgen()` instance**
- **Don't repeat the same layout** across all slides — vary columns, cards, callouts

## CRITICAL: No network calls — the script runs in a sandboxed subprocess

The script has **no internet access** and must not make any network calls.
- **No** `fetch`, `axios`, `https.get`, `http.get`, or any URL requests
- **No** downloading images, fonts, or templates from the internet
- All content and data must be hardcoded in the script itself
- The script must complete in under 30 seconds
