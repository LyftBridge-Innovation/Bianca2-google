# PDF Generation Instructions

Use `reportlab` (Python). Write complete, self-contained Python code that creates a `.pdf` file in the current working directory.

## Simple PDF with reportlab canvas

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("output.pdf", pagesize=letter)
width, height = letter   # 612 x 792 points (1 inch = 72 points)

# Text
c.setFont("Helvetica-Bold", 24)
c.drawString(72, height - 100, "Document Title")

c.setFont("Helvetica", 12)
c.drawString(72, height - 140, "Body text line here")

# Horizontal rule
c.setStrokeColorRGB(0.8, 0.8, 0.8)
c.line(72, height - 120, width - 72, height - 120)

# New page
c.showPage()

c.save()
```

## Structured PDF with Platypus (recommended for longer documents)

```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)

doc = SimpleDocTemplate(
    "output.pdf",
    pagesize=letter,
    leftMargin=inch, rightMargin=inch,
    topMargin=inch, bottomMargin=inch
)

styles = getSampleStyleSheet()
story = []

# Title
story.append(Paragraph("Report Title", styles['Title']))
story.append(Spacer(1, 0.3 * inch))

# Heading
story.append(Paragraph("Section 1", styles['Heading1']))
story.append(Spacer(1, 0.1 * inch))

# Body text
story.append(Paragraph("This is the body text.", styles['Normal']))
story.append(Spacer(1, 0.2 * inch))

# Horizontal rule
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC")))
story.append(Spacer(1, 0.2 * inch))

# Table
data = [
    ['Column A', 'Column B', 'Column C'],
    ['Row 1 A',  'Row 1 B',  'Row 1 C'],
    ['Row 2 A',  'Row 2 B',  'Row 2 C'],
]
table = Table(data, colWidths=[2 * inch, 2 * inch, 2 * inch])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E75B6")),
    ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
    ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE',   (0, 0), (-1, 0), 11),
    ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
    ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
    ('TOPPADDING',  (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
]))
story.append(table)
story.append(Spacer(1, 0.3 * inch))

# Page break
story.append(PageBreak())

doc.build(story)
```

## Custom Styles

```python
custom_heading = ParagraphStyle(
    'CustomHeading',
    parent=styles['Normal'],
    fontSize=16,
    fontName='Helvetica-Bold',
    textColor=colors.HexColor("#2E75B6"),
    spaceAfter=8,
    spaceBefore=16,
)

custom_body = ParagraphStyle(
    'CustomBody',
    parent=styles['Normal'],
    fontSize=11,
    leading=16,      # Line height
    spaceAfter=8,
)

story.append(Paragraph("Custom Heading", custom_heading))
story.append(Paragraph("Body text with custom style.", custom_body))
```

## Subscripts and Superscripts

**NEVER use Unicode sub/superscript characters** — they render as black boxes in built-in fonts.

```python
# ✅ CORRECT — use ReportLab XML tags inside Paragraph
chemical = Paragraph("H<sub>2</sub>O and CO<sub>2</sub>", styles['Normal'])
squared   = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])
```

## Multi-column Layout

```python
from reportlab.platypus import BalancedColumns

cols = BalancedColumns(
    story_parts,
    nCols=2,
    needed=72,
)
main_story.append(cols)
```

## Units Quick Reference

- 1 inch = 72 points
- US Letter = 612 × 792 pts (8.5" × 11")
- A4 = 595 × 842 pts

## Critical Rules

- **Never use Unicode sub/superscripts** — use `<sub>` and `<super>` XML tags in Paragraph
- **Set margins explicitly** — reportlab defaults are fine but state them clearly
- **Use `Spacer(1, N * inch)`** between sections for breathing room
- **Tables require `setStyle`** for professional appearance — plain tables look bare
- **Match `colWidths` sum to available page width** (page width - left margin - right margin)
