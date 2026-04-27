# DOCX Generation Instructions

Use the `docx` npm package (installed globally as `docx`). Write complete, self-contained JavaScript that creates a `.docx` file in the current working directory.

## Setup

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink,
        HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
        PageNumber, PageBreak, TableOfContents } = require('docx');
const fs = require('fs');

const doc = new Document({ sections: [{ children: [/* content */] }] });
Packer.toBuffer(doc).then(buffer => fs.writeFileSync("output.docx", buffer));
```

## Page Size — Always Set Explicitly

```javascript
sections: [{
  properties: {
    page: {
      size: { width: 12240, height: 15840 },         // US Letter in DXA (1440 = 1 inch)
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
    }
  },
  children: [/* content */]
}]
```

## Styles (Override Built-in Headings)

```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{ children: [] }]
});
```

## Lists — NEVER use unicode bullets

```javascript
// ✅ CORRECT
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{ children: [
    new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun("Bullet")] }),
    new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun("Numbered")] }),
  ]}]
});
```

## Tables — CRITICAL: dual widths required

```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

new Table({
  width: { size: 9360, type: WidthType.DXA },    // Always DXA — never PERCENTAGE
  columnWidths: [4680, 4680],                      // Must sum to table width
  rows: [
    new TableRow({ children: [
      new TableCell({
        borders,
        width: { size: 4680, type: WidthType.DXA }, // Must match columnWidth
        shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun("Cell")] })]
      }),
    ]})
  ]
})
```

## Headers / Footers

```javascript
sections: [{
  properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
  headers: {
    default: new Header({ children: [new Paragraph({ children: [new TextRun("Header text")] })] })
  },
  footers: {
    default: new Footer({ children: [new Paragraph({
      children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] })]
    })] })
  },
  children: [/* content */]
}]
```

## Page Breaks

```javascript
// CRITICAL: PageBreak must be inside a Paragraph
new Paragraph({ children: [new PageBreak()] })
```

## Hyperlinks

```javascript
new Paragraph({ children: [
  new ExternalHyperlink({
    children: [new TextRun({ text: "Click here", style: "Hyperlink" })],
    link: "https://example.com",
  })
]})
```

## Critical Rules

- **Set page size explicitly** — defaults to A4; use US Letter (12240 x 15840) for US documents
- **Never use `\n`** — use separate Paragraph elements
- **Never use unicode bullets** — use `LevelFormat.BULLET` with numbering config
- **PageBreak must be in Paragraph** — standalone creates invalid XML
- **Always use `WidthType.DXA`** for tables — never `WidthType.PERCENTAGE` (breaks in Google Docs)
- **Tables need dual widths** — `columnWidths` array AND cell `width`, both must match
- **Use `ShadingType.CLEAR`** — never SOLID for table shading
- **Override built-in styles** — use exact IDs: "Heading1", "Heading2" with `outlineLevel`

## CRITICAL: No network calls — the script runs in a sandboxed subprocess

The script has **no internet access** and must not make any network calls.
- **No** `fetch`, `axios`, `https.get`, `http.get`, or any URL requests
- **No** downloading images, fonts, or templates from the internet
- All content must be hardcoded in the script itself
- The script must complete in under 30 seconds
