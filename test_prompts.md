Here are 5 prompts that cover each format and exercise the full pipeline end-to-end:

---

**1. PPTX — pitch deck (tests pptxgenjs + design rules)**
> "Create a 6-slide pitch deck for a B2B SaaS startup called Meridian that sells AI-powered supply chain software. Include a title slide, problem, solution, market size, traction, and a call to action. Use a professional dark blue color theme."

This hits the `pptx` keyword → injects pptx instructions → Gemini writes pptxgenjs code → background task → Drive link.

---

**2. XLSX — financial model (tests openpyxl + formula requirement)**
> "Build me an Excel spreadsheet with a 12-month P&L model for a SaaS company. Include rows for MRR, churn, new revenue, COGS, gross profit, and net income. Use formulas to calculate everything — don't hardcode totals."

Tests the formula-first rule and multi-sheet capability.

---

**3. DOCX — formal document (tests docx-js + table + heading styles)**
> "Write me a Word document — a vendor evaluation report comparing three cloud providers (AWS, GCP, Azure) across five criteria: pricing, support, reliability, compliance, and integrations. Include a summary table and proper headings."

Tests table rendering, heading styles, and page layout.

---

**4. PDF — invoice/report (tests reportlab + structured layout)**
> "Generate a PDF invoice for a consulting project. Client is Acme Corp, billed for 40 hours of strategy consulting at $250/hr, plus a $500 travel expense. Include a clean table, totals row, and payment terms at the bottom."

Tests reportlab Platypus, table styling, and structured multi-section layout.

---

**5. XLSX — tracker (tests keyword matching on "tracker" + multiple sheets)**
> "Make me a project tracker spreadsheet for a product launch. I need a task list sheet with columns for task name, owner, due date, status, and priority — and a summary sheet that shows counts of tasks by status using formulas."

Tests that `tracker` in the message correctly triggers xlsx instructions, and exercises cross-sheet formula references.

---

After sending each prompt, look for:
1. A `tool_call` SSE event with `status: "queued"` — confirms routing to background task
2. The Tasks tab in Neural Config showing the task as running/complete
3. A Google Drive URL in the final response