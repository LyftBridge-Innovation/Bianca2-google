"""
Document engine — executes LLM-generated code to produce formatted binary files,
then uploads the result to Google Drive.

Supported formats:
  docx — JavaScript via docx          (npm-installed locally per run)
  xlsx — Python via openpyxl          (pip install openpyxl)
  pptx — JavaScript via pptxgenjs     (npm-installed locally per run)
  pdf  — Python via reportlab         (pip install reportlab)

JS packages are installed into the temp working directory before execution so
no global npm packages are required.
"""
import os
import re
import sys
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path

from tools.drive_uploader import upload_file_to_drive

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT = 120  # seconds
NPM_INSTALL_TIMEOUT = 120  # seconds — fallback for local dev only

# npm packages required per document type
_JS_PACKAGES: dict[str, list[str]] = {
    "pptx": ["pptxgenjs"],
    "docx": ["docx"],
}

# Pre-installed node_modules baked into the Docker image at build time.
# On Cloud Run this path always exists — symlinked at runtime, zero npm calls.
_PREINSTALLED_NODE_MODULES = "/app/npm_deps/node_modules"

# ── Filename helpers ──────────────────────────────────────────────────────────

def _safe_stem(title: str) -> str:
    """Convert a document title to a filesystem-safe base name."""
    stem = re.sub(r'[^\w\s-]', '', title).strip()
    stem = re.sub(r'[\s-]+', '_', stem)
    return stem[:80] or "document"


def _output_filename(title: str, document_type: str) -> str:
    return f"{_safe_stem(title)}.{document_type}"


# ── Code normalisation ────────────────────────────────────────────────────────

def _patch_js_output_path(code: str, output_file: str) -> str:
    """
    Ensure the JS code writes to output_file in the CWD.

    docx-js uses:  Packer.toBuffer(doc).then(b => fs.writeFileSync("name.docx", b))
    pptxgenjs uses: pres.writeFile({ fileName: "name.pptx" })

    We normalise both to write to the expected filename.
    """
    # pptxgenjs: replace fileName value
    code = re.sub(
        r'writeFile\s*\(\s*\{[^}]*fileName\s*:\s*["\'][^"\']*["\']',
        f'writeFile({{ fileName: "{output_file}"',
        code,
    )
    # docx-js Packer.toBuffer style: replace writeFileSync filename arg
    code = re.sub(
        r'writeFileSync\s*\(\s*["\'][^"\']*["\']',
        f'writeFileSync("{output_file}"',
        code,
    )
    # Also catch pres.writeFile("filename.pptx") shorthand
    code = re.sub(
        r'writeFile\s*\(\s*["\'][^"\']*["\']',
        f'writeFile("{output_file}"',
        code,
    )
    return code


def _patch_py_output_path(code: str, output_file: str) -> str:
    """
    Ensure the Python code saves to output_file in the CWD.

    openpyxl: wb.save("name.xlsx")
    reportlab: c.save() / doc.build() — these need the filename set earlier.
    We replace any .save("...") / .save('...') with the correct name.
    """
    # openpyxl wb.save(...)
    code = re.sub(
        r'\.save\s*\(\s*["\'][^"\']*["\']',
        f'.save("{output_file}"',
        code,
    )
    # reportlab Canvas("filename.pdf", ...)
    code = re.sub(
        r'Canvas\s*\(\s*["\'][^"\']*["\']',
        f'Canvas("{output_file}"',
        code,
    )
    # reportlab SimpleDocTemplate("filename.pdf", ...)
    code = re.sub(
        r'SimpleDocTemplate\s*\(\s*["\'][^"\']*["\']',
        f'SimpleDocTemplate("{output_file}"',
        code,
    )
    return code


# ── Execution ─────────────────────────────────────────────────────────────────

def _npm_install(packages: list[str], work_dir: str) -> None:
    """
    Make npm packages available in work_dir for the generated script.

    On Cloud Run: symlinks the pre-installed node_modules from the Docker image
    (baked in at build time) — no network calls, no timeout risk.

    Local dev fallback: runs npm install if the pre-installed path doesn't exist.
    """
    # Write a minimal package.json directly — no need for `npm init -y`
    pkg_json_path = os.path.join(work_dir, "package.json")
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        f.write('{"name":"bianca-doc","version":"1.0.0","private":true}\n')

    node_modules_dest = os.path.join(work_dir, "node_modules")

    if os.path.isdir(_PREINSTALLED_NODE_MODULES):
        # Fast path: symlink pre-installed modules (Docker image)
        os.symlink(_PREINSTALLED_NODE_MODULES, node_modules_dest)
        logger.info("Using pre-installed node_modules from %s", _PREINSTALLED_NODE_MODULES)
    else:
        # Local dev fallback: install from npm registry
        result = subprocess.run(
            ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"] + packages,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=NPM_INSTALL_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"npm install {packages} failed (exit {result.returncode}).\n"
                f"stderr: {result.stderr.strip()[:500]}"
            )
        logger.info("npm install %s → OK (local)", packages)


def _wrap_in_async_runner(user_code: str, output_file: str) -> str:
    """
    Produce a reliable pptxgenjs runner script.

    Strategy: write the user's code into a self-contained async function,
    ensure writeFile is awaited, and use a top-level .then/.catch so Node
    stays alive until the file is fully flushed to disk regardless of whether
    the LLM used await or .then().
    """
    # Normalise the writeFile call to the correct output filename
    # (already done by _patch_js_output_path, but be defensive)
    user_code = re.sub(
        r'(?:await\s+)?pres\.writeFile\s*\([^)]*\)',
        f'await pres.writeFile({{ fileName: "{output_file}" }})',
        user_code,
    )
    # Remove any standalone .then()/.catch() chains left after the above
    user_code = re.sub(r'\s*\.then\s*\([^)]*\)', '', user_code)
    user_code = re.sub(r'\s*\.catch\s*\([^)]*\)', '', user_code)

    return f"""\
(async function run() {{
{user_code}
}})()
.then(() => process.exit(0))
.catch(err => {{
  console.error('pptx generation failed:', err && err.message ? err.message : String(err));
  process.exit(1);
}});
"""


def _run_node(code: str, output_file: str, work_dir: str, document_type: str) -> None:
    """Install required npm packages, write JS to a temp file, and execute with Node."""
    packages = _JS_PACKAGES.get(document_type, [])
    if packages:
        _npm_install(packages, work_dir)

    script_path = os.path.join(work_dir, "generate.js")
    patched = _patch_js_output_path(code, output_file)

    # pptxgenjs writeFile is async — wrap in a reliable async runner
    if document_type == "pptx":
        patched = _wrap_in_async_runner(patched, output_file)

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(patched)

    result = subprocess.run(
        ["node", script_path],
        cwd=work_dir,
        capture_output=True,
        text=True,
        timeout=EXECUTION_TIMEOUT,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        raise RuntimeError(
            f"Node execution failed (exit {result.returncode}).\n"
            f"stderr: {stderr[:1000]}\nstdout: {stdout[:500]}"
        )


def _run_python(code: str, output_file: str, work_dir: str) -> None:
    """Write Python to a temp file and execute it with the current interpreter."""
    script_path = os.path.join(work_dir, "generate.py")
    patched = _patch_py_output_path(code, output_file)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(patched)

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=work_dir,
        capture_output=True,
        text=True,
        timeout=EXECUTION_TIMEOUT,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        raise RuntimeError(
            f"Python execution failed (exit {result.returncode}).\n"
            f"stderr: {stderr[:1000]}\nstdout: {stdout[:500]}"
        )


# ── Core executor ─────────────────────────────────────────────────────────────

def execute_and_upload(
    user_id: str,
    document_type: str,
    title: str,
    code: str,
) -> dict:
    """
    Execute LLM-generated document creation code, upload the result to Drive.

    Args:
        user_id:       User whose Drive credentials are used.
        document_type: "docx" | "xlsx" | "pptx" | "pdf"
        title:         Human-readable document title (used as filename).
        code:          Complete generation code (JS for docx/pptx, Python for xlsx/pdf).

    Returns:
        {"url": str, "title": str, "file_id": str, "format": str}
    """
    output_file = _output_filename(title, document_type)
    work_dir = tempfile.mkdtemp(prefix="bianca_doc_")
    logger.info(
        "Generating %s '%s' in %s for user %s",
        document_type, title, work_dir, user_id,
    )

    try:
        if document_type in ("docx", "pptx"):
            _run_node(code, output_file, work_dir, document_type)
        elif document_type in ("xlsx", "pdf"):
            _run_python(code, output_file, work_dir)
        else:
            raise ValueError(f"Unsupported document_type: {document_type!r}")

        output_path = os.path.join(work_dir, output_file)
        if not os.path.exists(output_path):
            # Try to find any file with the right extension
            candidates = list(Path(work_dir).glob(f"*.{document_type}"))
            if not candidates:
                raise FileNotFoundError(
                    f"Expected output file '{output_file}' not found in {work_dir}. "
                    f"Files present: {list(Path(work_dir).iterdir())}"
                )
            output_path = str(candidates[0])

        result = upload_file_to_drive(
            user_id=user_id,
            local_path=output_path,
            filename=output_file,
            document_type=document_type,
        )

        logger.info("Document '%s' uploaded to Drive: %s", title, result["url"])
        return {
            "url": result["url"],
            "title": title,
            "file_id": result["file_id"],
            "format": document_type,
        }

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ── Per-format thin wrappers (used as YAML tool handlers) ─────────────────────

def create_docx_document(user_id: str, title: str, code: str) -> dict:
    """Create a Word (.docx) document from docx-js code and upload to Drive."""
    return execute_and_upload(user_id, "docx", title, code)


def create_xlsx_spreadsheet(user_id: str, title: str, code: str) -> dict:
    """Create an Excel (.xlsx) spreadsheet from openpyxl code and upload to Drive."""
    return execute_and_upload(user_id, "xlsx", title, code)


def create_pptx_presentation(user_id: str, title: str, code: str) -> dict:
    """Create a PowerPoint (.pptx) presentation from pptxgenjs code and upload to Drive."""
    return execute_and_upload(user_id, "pptx", title, code)


def create_pdf_document(user_id: str, title: str, code: str) -> dict:
    """Create a PDF document from reportlab code and upload to Drive."""
    return execute_and_upload(user_id, "pdf", title, code)
