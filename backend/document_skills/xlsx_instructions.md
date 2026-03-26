# XLSX Generation Instructions

Use `openpyxl` (Python). Write complete, self-contained Python code that creates an `.xlsx` file in the current working directory.

## Setup

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
sheet = wb.active
sheet.title = "Sheet1"

# ... populate sheet ...

wb.save("output.xlsx")
```

## Adding Data

```python
# Direct cell assignment
sheet['A1'] = 'Revenue'
sheet['B1'] = 100000

# Append rows
sheet.append(['Q1', 'Q2', 'Q3', 'Q4'])
sheet.append([4500, 5500, 6200, 7100])

# Multiple sheets
sheet2 = wb.create_sheet('Summary')
sheet2['A1'] = 'Total'
```

## CRITICAL: Use Excel Formulas, Not Hardcoded Values

```python
# ❌ WRONG — hardcoding calculated values
total = sum([4500, 5500, 6200, 7100])
sheet['B10'] = total

# ✅ CORRECT — let Excel calculate
sheet['B10'] = '=SUM(B2:B9)'
sheet['C5'] = '=(C4-C2)/C2'         # Growth rate
sheet['D20'] = '=AVERAGE(D2:D19)'   # Average
```

## Formatting

```python
# Bold header
sheet['A1'].font = Font(bold=True, size=12, color='FFFFFF')
sheet['A1'].fill = PatternFill('solid', start_color='2E75B6')
sheet['A1'].alignment = Alignment(horizontal='center', vertical='center')

# Column width
sheet.column_dimensions['A'].width = 20
sheet.row_dimensions[1].height = 25

# Borders
thin = Side(style='thin', color='CCCCCC')
sheet['A1'].border = Border(left=thin, right=thin, top=thin, bottom=thin)

# Number format
sheet['B2'].number_format = '#,##0.00'    # Currency
sheet['C2'].number_format = '0.0%'        # Percentage
```

## Financial Model Color Standards

- **Blue text (0000FF)**: Hardcoded inputs users will change
- **Black text (000000)**: All formulas and calculations
- **Green text (008000)**: Links pulling from other sheets
- **Yellow fill (FFFF00)**: Key assumptions needing attention

```python
# Blue input cell
sheet['B5'].font = Font(color='0000FF')

# Apply yellow background to assumption cells
sheet['B6'].fill = PatternFill('solid', start_color='FFFF00')
```

## Multiple Sheets Example

```python
wb = Workbook()

# Summary sheet
summary = wb.active
summary.title = 'Summary'
summary['A1'] = 'Dashboard'

# Data sheet
data = wb.create_sheet('Data')
data.append(['Month', 'Revenue', 'Costs', 'Profit'])
for i, month in enumerate(['Jan','Feb','Mar'], start=2):
    data[f'A{i}'] = month
    data[f'B{i}'] = 10000 * i
    data[f'C{i}'] = 7000 * i
    data[f'D{i}'] = f'=B{i}-C{i}'

wb.save("output.xlsx")
```

## Critical Rules

- **Always use formulas** instead of hardcoded calculated values — spreadsheet must stay dynamic
- **Document sources** for hardcoded data in cell comments or adjacent cells
- **Zero formula errors** — verify no #REF!, #DIV/0!, #VALUE!, #N/A, #NAME?
- **Professional font** — use Arial or Calibri consistently
- **Preserve existing templates** when modifying — never override established patterns
- **Use `data_only=True`** only for reading (saves strip formulas permanently if resaved)
