"""LangChain tool registry — YAML skill configs + direct Python tools."""
import logging
from langchain.tools import tool as langchain_tool
from skills_loader import get_yaml_langchain_tools
from tools.gemini_research import build_gemini_research_tools

logger = logging.getLogger(__name__)


@langchain_tool
def create_and_email_document(
    document_type: str,
    title: str,
    code: str,
    to: str,
    subject: str,
    body: str,
) -> str:
    """Create a document (pdf/docx/pptx/xlsx) and automatically email it with a
    Drive link once it has been generated and uploaded.

    Use this — and ONLY this — when the user asks to both create a document AND
    send it to someone in the same request. Do NOT call a document tool and
    send_email_message separately for this case.

    Args:
        document_type: One of pdf, docx, pptx, xlsx.
        title:         Human-readable document title used as the filename.
        code:          Complete generation code — docx-js / pptxgenjs (JS) for
                       docx/pptx, openpyxl / reportlab (Python) for xlsx/pdf.
        to:            Recipient email address.
        subject:       Email subject line.
        body:          Email body text (the Drive link will be appended automatically).
    """
    from task_service import task_service
    from request_context import current_user_id

    user_id = current_user_id.get()
    params = {
        "document_type": document_type,
        "title": title,
        "code": code,
        "next_task": {
            "type": "send_email",
            "parameters": {"to": to, "subject": subject, "body": body},
        },
    }
    task = task_service.create_task(user_id, "create_document", params)
    task_service.enqueue(task.task_id)
    logger.info(
        "create_and_email_document: queued create_document task %s for user %s → will email to %s",
        task.task_id, user_id, to,
    )
    return (
        f"Creating {document_type.upper()} '{title}' in the background. "
        f"Once it's uploaded to Drive it will be emailed automatically to {to} "
        f"with the Drive link included so they can open it directly."
    )


_yaml_tools            = get_yaml_langchain_tools()
_gemini_research_tools = build_gemini_research_tools()

ALL_TOOLS = _yaml_tools + _gemini_research_tools + [create_and_email_document]
logger.info(
    "Loaded %d tools total (%d YAML, %d Gemini Research, 1 create_and_email_document)",
    len(ALL_TOOLS), len(_yaml_tools), len(_gemini_research_tools),
)
