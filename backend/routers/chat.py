"""Chat endpoint for the AI Chief of Staff using Gemini + LangChain."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import json
from langchain_google_vertexai import ChatVertexAI
from config import GCP_PROJECT_ID, GCP_LOCATION, TEST_USER_ID
from request_context import current_user_id
from prompts import get_system_prompt
from langchain_tools import ALL_TOOLS
from models import FirestoreCollections, Session, Message, ToolCall, ToolActionLog
from memory_utils import generate_human_readable
from summarization import summarize_session_sync
from memory_retrieval import retrieve_memories_for_message, format_memory_injection
from skill_matcher import match_skills, build_skills_block
from settings_loader import load_settings
from task_service import task_service
from document_skill_loader import get_document_skill_block, detect_document_type, extract_doc_title
import logging as _logging
_chat_logger = _logging.getLogger(__name__)

# ── Background task queue integration ─────────────────────────────────────────
# Tool names that should be routed through the background task queue instead
# of being executed synchronously in the chat loop.
BACKGROUND_TOOL_MAP = {
    # Document creation tools — all map to the unified create_document executor
    "create_docx_document": "create_document",
    "create_xlsx_spreadsheet": "create_document",
    "create_pptx_presentation": "create_document",
    "create_pdf_document": "create_document",
    # Email tools
    "send_email_message": "send_email",
    "draft_email_message": "draft_email",
}

router = APIRouter(prefix="/chat", tags=["chat"])


def _sanitize_messages(messages: list) -> list:
    """
    Gemini rejects any message whose content is an empty string or empty list.
    Replace empty-content AIMessages (produced during tool-call turns) with a
    single-space placeholder so Vertex AI doesn't reject the whole request with
    'must include at least one parts field'.
    """
    from langchain_core.messages import AIMessage
    sanitized = []
    for msg in messages:
        if isinstance(msg, AIMessage) and (msg.content == "" or msg.content == []):
            # Preserve tool_calls; just give it a non-empty text body
            sanitized.append(AIMessage(content=" ", tool_calls=msg.tool_calls or []))
        else:
            sanitized.append(msg)
    return sanitized

# Max number of past messages (user + assistant combined) included in each LLM
# call.  The full history is always persisted in Firestore; this only controls
# how many turns are sent as context to Gemini per request.
MAX_HISTORY_MESSAGES = 20


_DOCUMENT_TOOL_TYPES = {
    "create_docx_document": "docx",
    "create_xlsx_spreadsheet": "xlsx",
    "create_pptx_presentation": "pptx",
    "create_pdf_document": "pdf",
}


def _try_enqueue_background(tool_name: str, tool_args: dict, user_id: str, session_id: str):
    """If tool_name is a long-running operation, enqueue it as a background task.

    Returns (True, result_str) if enqueued, or (False, None) if tool should
    run synchronously in the normal chat loop.
    """
    task_type = BACKGROUND_TOOL_MAP.get(tool_name)
    if not task_type:
        return False, None

    # For document creation tasks, add document_type so the executor knows
    # which format to generate.
    params = dict(tool_args)
    if doc_type := _DOCUMENT_TOOL_TYPES.get(tool_name):
        params["document_type"] = doc_type

    task = task_service.create_task(
        user_id=user_id,
        task_type=task_type,
        parameters=params,
        session_id=session_id,
    )
    task_service.enqueue(task.task_id)

    friendly = task_type.replace("_", " ")
    result_str = (
        f"Background task created (ID: {task.task_id}). "
        f"I've queued a '{friendly}' operation that will run in the background. "
        f"The user can track its progress in the Tasks tab of Neural Config."
    )
    return True, result_str

def _load_user_prompt_context(user_id: str) -> dict:
    """
    Load world model entries and access control (authorizations + constraints)
    for a user from Firestore. Failures are silenced — returns empty lists.
    """
    result = {"world_model": [], "authorizations": [], "constraints": []}
    try:
        from firestore_client import get_firestore_client
        db = get_firestore_client()
        user_ref = db.collection("users").document(user_id)

        wm_docs = user_ref.collection("world_model").stream()
        result["world_model"] = [d.to_dict() for d in wm_docs]

        ac_doc = user_ref.collection("access_control").document("config").get()
        if ac_doc.exists:
            ac = ac_doc.to_dict()
            result["authorizations"] = ac.get("authorizations", [])
            result["constraints"] = ac.get("constraints", [])
    except Exception:
        pass
    return result


# LLM cache — recreated when model/temperature settings change
_llm_cache: dict = {"model": None, "temperature": None, "api_key": None, "instance": None}


def _get_llm():
    """
    Return the LLM instance for the currently configured model.

    Supports two providers:
      - Anthropic  : any model whose name starts with "claude"
      - Vertex AI  : everything else (gemini-*)

    The instance is cached and recreated only when settings change.
    """
    import os
    settings = load_settings()
    model: str = settings.get("model", "gemini-2.5-flash")
    temperature: float = settings.get("temperature", 0.7)

    # Resolve Google API key: settings override → env var
    google_key: str = (
        settings.get("google_api_key", "").strip()
        or os.getenv("GOOGLE_API_KEY", "")
    )

    # Resolve Anthropic key: settings override → env var
    anthropic_key: str = (
        settings.get("anthropic_api_key", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "")
    )

    if (
        _llm_cache["instance"] is None
        or _llm_cache["model"] != model
        or _llm_cache["temperature"] != temperature
        or _llm_cache["api_key"] != (google_key or anthropic_key)
    ):
        _llm_cache["model"] = model
        _llm_cache["temperature"] = temperature
        _llm_cache["api_key"] = google_key or anthropic_key

        if model.startswith("claude"):
            from langchain_anthropic import ChatAnthropic
            if not anthropic_key:
                raise ValueError(
                    "Anthropic API key is required for Claude models. "
                    "Add ANTHROPIC_API_KEY to backend/.env or set it in Neural Config → System Prompt."
                )
            _llm_cache["instance"] = ChatAnthropic(
                model=model,
                temperature=temperature,
                api_key=anthropic_key,
                max_retries=4,
                # 60s timeout — prevents cold-start TCP failures to api.anthropic.com
                timeout=60.0,
            ).bind_tools(ALL_TOOLS)
            _chat_logger.info("LLM: Anthropic %s (direct)", model)
        elif google_key:
            # Direct AI Studio key provided — use Google GenAI (non-Vertex) client
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm_cache["instance"] = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=google_key,
                max_retries=6,
            ).bind_tools(ALL_TOOLS)
            _chat_logger.info("LLM: Google GenAI (AI Studio) %s", model)
        else:
            # No explicit key — fall back to Vertex AI with Application Default Credentials
            _llm_cache["instance"] = ChatVertexAI(
                model=model,
                project=GCP_PROJECT_ID,
                location=GCP_LOCATION,
                temperature=temperature,
                max_retries=6,
            ).bind_tools(ALL_TOOLS)
            _chat_logger.info("LLM: Vertex AI %s", model)

    return _llm_cache["instance"]


# Initialize Firestore collections
fs = FirestoreCollections()

# ── Request/Response Models ───────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # If provided, resume existing session
    user_id: str = TEST_USER_ID  # Default to test user for now


class ChatResponse(BaseModel):
    response: str
    session_id: str
    history: list[ChatMessage]

# ── Chat Endpoint ─────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Main chat endpoint with Phase 3A session persistence and Phase 3B summarization.
    Creates or resumes a session, persists all messages and tool calls to Firestore.
    When creating a new session, triggers summarization of previous session as background task.
    """
    try:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

        # Set per-request user context for LangChain tools
        current_user_id.set(request.user_id)

        # Get or create session
        if request.session_id:
            # Resume existing session
            session = fs.get_session(request.session_id)
            if not session:
                raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
        else:
            # Check if user has an existing active session (Phase 3B)
            previous_session = fs.get_active_session_for_user(request.user_id)
            
            # Create new session
            session = Session(user_id=request.user_id, modality="chat")
            fs.create_session(session)
            
            # Trigger summarization of previous session as background task (non-blocking)
            if previous_session:
                background_tasks.add_task(
                    summarize_session_sync,
                    user_id=request.user_id,
                    session_id=previous_session.session_id
                )
        
        # Persist user message to session
        user_message = Message(role="user", content=request.message)
        fs.append_message(session.session_id, user_message)
        
        # Load user-specific context (world model + access control)
        user_ctx = _load_user_prompt_context(request.user_id)

        # Build message chain with system prompt and session history
        messages = [SystemMessage(content=get_system_prompt(
            world_model=user_ctx["world_model"],
            authorizations=user_ctx["authorizations"],
            constraints=user_ctx["constraints"],
        ))]
        
        # Add recent messages from session history (capped to avoid token limits)
        for msg in session.messages[-MAX_HISTORY_MESSAGES:]:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        # Add current user message
        messages.append(HumanMessage(content=request.message))
        
        # ── Phase 3C: Retrieve and inject memories ───────────────────────────
        memory_data = retrieve_memories_for_message(
            user_message=request.message,
            user_id=request.user_id
        )
        
        # Inject into system prompt if memories exist
        if memory_data["total_count"] > 0:
            memory_block = format_memory_injection(
                event_memories=memory_data["event_memories"],
                entity_memories=memory_data["entity_memories"]
            )
            
            # Update system message (first message in chain)
            original_system_prompt = get_system_prompt(
                world_model=user_ctx["world_model"],
                authorizations=user_ctx["authorizations"],
                constraints=user_ctx["constraints"],
            )
            enriched_system_prompt = f"{original_system_prompt}\n\n{memory_block}"
            messages[0] = SystemMessage(content=enriched_system_prompt)
            
            from logging import getLogger
            logger = getLogger(__name__)
            logger.info(f"Injected {memory_data['total_count']} memories (window: {memory_data['recency_window_days']} days)")
        # ────────────────────────────────────────────────────────────────────

        # ── Skill matching: inject relevant per-user skills ────────────────
        user_skills_raw = fs.get_user_skills_for_matching(request.user_id)
        if user_skills_raw:
            skill_tuples = [(s['skill_id'], s['title'], s['content']) for s in user_skills_raw]
            matched = match_skills(request.message, skill_tuples)
            skills_block = build_skills_block(matched)
            if skills_block:
                current_prompt = messages[0].content
                messages[0] = SystemMessage(content=f"{current_prompt}\n\n{skills_block}")
        # ────────────────────────────────────────────────────────────────────

        # ── Document skill injection ──────────────────────────────────────
        doc_skill_block = get_document_skill_block(request.message)
        if doc_skill_block:
            current_prompt = messages[0].content
            messages[0] = SystemMessage(content=f"{current_prompt}\n\n{doc_skill_block}")
        # ────────────────────────────────────────────────────────────────────

        # Track tool calls for logging
        session_tool_calls = []
        
        # Invoke LLM with tools
        response = _get_llm().invoke(_sanitize_messages(messages))
        
        # Handle tool calls if present
        max_iterations = 5
        iteration = 0
        
        while response.tool_calls and iteration < max_iterations:
            iteration += 1
            messages.append(response)
            
            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Check if this should be a background task
                enqueued, bg_result = _try_enqueue_background(
                    tool_name, tool_args, request.user_id, session.session_id
                )

                if enqueued:
                    tool_result = bg_result
                    result_str = bg_result

                    # Log the background enqueue as a tool call
                    tc = ToolCall(
                        tool_name=tool_name,
                        parameters=tool_args,
                        result=result_str
                    )
                    session_tool_calls.append(tc)
                    fs.append_tool_call(session.session_id, tc)

                    human_readable = f"Queued background task: {tool_name.replace('_', ' ')}"
                    action_log = ToolActionLog(
                        user_id=request.user_id,
                        session_id=session.session_id,
                        tool_name=tool_name,
                        human_readable=human_readable,
                        parameters=tool_args,
                        result=result_str,
                        modality="chat"
                    )
                    fs.log_tool_action(action_log)
                else:
                    # Find and execute the tool synchronously
                    tool_result = None
                    for tool in ALL_TOOLS:
                        if tool.name == tool_name:
                            try:
                                tool_result = tool.invoke(tool_args)
                                result_str = str(tool_result)

                                # Log tool call to session
                                tc = ToolCall(
                                    tool_name=tool_name,
                                    parameters=tool_args,
                                    result=result_str
                                )
                                session_tool_calls.append(tc)
                                fs.append_tool_call(session.session_id, tc)

                                # Generate human readable description
                                human_readable = generate_human_readable(tool_name, tool_args, result_str)

                                # Log to global tool_action_log
                                action_log = ToolActionLog(
                                    user_id=request.user_id,
                                    session_id=session.session_id,
                                    tool_name=tool_name,
                                    human_readable=human_readable,
                                    parameters=tool_args,
                                    result=result_str,
                                    modality="chat"
                                )
                                fs.log_tool_action(action_log)

                            except Exception as e:
                                tool_result = f"Error executing {tool_name}: {str(e)}"
                            break
                
                # Add tool result to messages
                messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"]
                ))
            
            # Get next response from LLM
            response = _get_llm().invoke(_sanitize_messages(messages))
        
        # Extract final text response
        if isinstance(response.content, str):
            ai_response = response.content
        elif isinstance(response.content, list):
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            ai_response = " ".join(text_parts) if text_parts else "I've completed your request."
        else:
            ai_response = str(response.content)
        
        # Persist assistant message to session
        assistant_message = Message(role="assistant", content=ai_response)
        fs.append_message(session.session_id, assistant_message)
        
        # Build history for response (fetch fresh from Firestore to ensure consistency)
        updated_session = fs.get_session(session.session_id)
        history = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in updated_session.messages
        ]

        return ChatResponse(
            response=ai_response,
            session_id=session.session_id,
            history=history,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ── Streaming Chat Endpoint (Phase 4A) ───────────────────────────────────────

def format_sse_event(event_type: str, data: dict) -> str:
    """Format data as Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(request: ChatRequest, background_tasks: BackgroundTasks) -> AsyncGenerator[str, None]:
    """
    Generator function for SSE streaming.
    Yields events: session, tool_call, token, done
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Set per-request user context for LangChain tools
        current_user_id.set(request.user_id)

        # Get or create session
        if request.session_id:
            session = fs.get_session(request.session_id)
            if not session:
                yield format_sse_event("error", {"message": f"Session {request.session_id} not found"})
                return
        else:
            previous_session = fs.get_active_session_for_user(request.user_id)
            session = Session(user_id=request.user_id, modality="chat")
            fs.create_session(session)
            
            if previous_session:
                background_tasks.add_task(
                    summarize_session_sync,
                    user_id=request.user_id,
                    session_id=previous_session.session_id
                )
        
        # Send session event first
        yield format_sse_event("session", {"session_id": session.session_id})
        
        # Persist user message
        user_message_obj = Message(role="user", content=request.message)
        fs.append_message(session.session_id, user_message_obj)

        # ── Early document-creation intercept ─────────────────────────────────
        # Detect document intent before any LLM call and queue immediately so
        # the user gets an instant response while generation runs in background.
        doc_type = detect_document_type(request.message)
        if doc_type:
            import os
            _settings = load_settings()
            title = extract_doc_title(request.message, doc_type)
            doc_task = task_service.create_task(
                user_id=request.user_id,
                task_type="generate_and_create_document",
                parameters={
                    "user_message": request.message,
                    "document_type": doc_type,
                    "title": title,
                    "model": _settings.get("model", "claude-sonnet-4-6"),
                    "anthropic_api_key": (
                        _settings.get("anthropic_api_key", "").strip()
                        or os.environ.get("ANTHROPIC_API_KEY", "")
                    ),
                },
                session_id=session.session_id,
            )
            task_service.enqueue(doc_task.task_id)

            type_labels = {
                "docx": "Word document", "xlsx": "Excel spreadsheet",
                "pptx": "PowerPoint presentation", "pdf": "PDF document",
            }
            instant_reply = (
                f"On it! I'm generating your **{type_labels[doc_type]}** — \"{title}\" — in the background. "
                f"This usually takes about 60–90 seconds (code generation + execution + Drive upload). "
                f"Check the **Tasks** tab for a live progress update and the Google Drive link once it's ready. "
                f"Task ID: `{doc_task.task_id}`"
            )
            assistant_msg = Message(role="assistant", content=instant_reply)
            fs.append_message(session.session_id, assistant_msg)
            yield format_sse_event("tool_call", {"tool": f"create_{doc_type}", "status": "queued"})
            yield format_sse_event("token", {"token": instant_reply})
            yield format_sse_event("done", {"session_id": session.session_id})
            return
        # ─────────────────────────────────────────────────────────────────────

        # Load user-specific context (world model + access control)
        user_ctx = _load_user_prompt_context(request.user_id)

        # Build message chain
        messages = [SystemMessage(content=get_system_prompt(
            world_model=user_ctx["world_model"],
            authorizations=user_ctx["authorizations"],
            constraints=user_ctx["constraints"],
        ))]
        
        # Add recent messages from session history (capped to avoid token limits)
        for msg in session.messages[-MAX_HISTORY_MESSAGES:]:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        messages.append(HumanMessage(content=request.message))
        
        # Phase 3C: Memory retrieval and injection
        memory_data = retrieve_memories_for_message(
            user_message=request.message,
            user_id=request.user_id
        )
        
        if memory_data["total_count"] > 0:
            memory_block = format_memory_injection(
                event_memories=memory_data["event_memories"],
                entity_memories=memory_data["entity_memories"]
            )
            original_system_prompt = get_system_prompt(
                world_model=user_ctx["world_model"],
                authorizations=user_ctx["authorizations"],
                constraints=user_ctx["constraints"],
            )
            enriched_system_prompt = f"{original_system_prompt}\n\n{memory_block}"
            messages[0] = SystemMessage(content=enriched_system_prompt)
            logger.info(f"Injected {memory_data['total_count']} memories")

        # Skill matching: inject relevant per-user skills
        user_skills_raw = fs.get_user_skills_for_matching(request.user_id)
        if user_skills_raw:
            skill_tuples = [(s['skill_id'], s['title'], s['content']) for s in user_skills_raw]
            matched = match_skills(request.message, skill_tuples)
            skills_block = build_skills_block(matched)
            if skills_block:
                current_prompt = messages[0].content
                messages[0] = SystemMessage(content=f"{current_prompt}\n\n{skills_block}")

        # Document skill injection
        doc_skill_block = get_document_skill_block(request.message)
        if doc_skill_block:
            current_prompt = messages[0].content
            messages[0] = SystemMessage(content=f"{current_prompt}\n\n{doc_skill_block}")

        # Track tool calls
        session_tool_calls = []
        
        # Run agentic loop FIRST (tool calls complete before streaming)
        response = _get_llm().invoke(_sanitize_messages(messages))
        
        max_iterations = 5
        iteration = 0
        
        while response.tool_calls and iteration < max_iterations:
            iteration += 1
            messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Check if this should be a background task
                enqueued, bg_result = _try_enqueue_background(
                    tool_name, tool_args, request.user_id, session.session_id
                )

                if enqueued:
                    # Emit tool_call event showing it was queued
                    yield format_sse_event("tool_call", {"tool": tool_name, "status": "queued"})

                    tool_result = bg_result
                    result_str = bg_result

                    tc = ToolCall(
                        tool_name=tool_name,
                        parameters=tool_args,
                        result=result_str
                    )
                    session_tool_calls.append(tc)
                    fs.append_tool_call(session.session_id, tc)

                    human_readable = f"Queued background task: {tool_name.replace('_', ' ')}"
                    action_log = ToolActionLog(
                        user_id=request.user_id,
                        session_id=session.session_id,
                        tool_name=tool_name,
                        human_readable=human_readable,
                        parameters=tool_args,
                        result=result_str,
                        modality="chat"
                    )
                    fs.log_tool_action(action_log)
                else:
                    # Emit tool_call event
                    yield format_sse_event("tool_call", {"tool": tool_name, "status": "running"})

                    tool_result = None
                    for tool in ALL_TOOLS:
                        if tool.name == tool_name:
                            try:
                                tool_result = tool.invoke(tool_args)
                                result_str = str(tool_result)

                                tc = ToolCall(
                                    tool_name=tool_name,
                                    parameters=tool_args,
                                    result=result_str
                                )
                                session_tool_calls.append(tc)
                                fs.append_tool_call(session.session_id, tc)

                                human_readable = generate_human_readable(tool_name, tool_args, result_str)
                                action_log = ToolActionLog(
                                    user_id=request.user_id,
                                    session_id=session.session_id,
                                    tool_name=tool_name,
                                    human_readable=human_readable,
                                    parameters=tool_args,
                                    result=result_str,
                                    modality="chat"
                                )
                                fs.log_tool_action(action_log)

                            except Exception as e:
                                tool_result = f"Error executing {tool_name}: {str(e)}"
                            break
                
                messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"]
                ))
            
            response = _get_llm().invoke(_sanitize_messages(messages))
        
        # Now stream the final response token by token
        # Need to reinvoke with streaming to get tokens
        accumulated_content = ""
        
        for chunk in _get_llm().stream(_sanitize_messages(messages)):
            if hasattr(chunk, 'content') and chunk.content:
                # Handle both string and list content from streaming chunks
                if isinstance(chunk.content, str):
                    token = chunk.content
                elif isinstance(chunk.content, list):
                    # Extract text from list of content blocks
                    text_parts = []
                    for block in chunk.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    token = "".join(text_parts)
                else:
                    token = str(chunk.content)
                
                if token:  # Only yield non-empty tokens
                    accumulated_content += token
                    yield format_sse_event("token", {"token": token})
        
        # If no streaming content (shouldn't happen), use the response we have
        if not accumulated_content:
            if isinstance(response.content, str):
                accumulated_content = response.content
            elif isinstance(response.content, list):
                text_parts = []
                for block in response.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                accumulated_content = " ".join(text_parts) if text_parts else "I've completed your request."
            else:
                accumulated_content = str(response.content)
            
            # Yield as single token if we had to fall back
            yield format_sse_event("token", {"token": accumulated_content})
        
        # Persist assistant message
        assistant_message = Message(role="assistant", content=accumulated_content)
        fs.append_message(session.session_id, assistant_message)
        
        # Send done event
        yield format_sse_event("done", {"session_id": session.session_id})
        
    except Exception as e:
        import traceback
        logger.error(f"Streaming error [{type(e).__name__}]: {e}\n{traceback.format_exc()}")
        yield format_sse_event("error", {"message": str(e)})


@router.post("/stream")
async def chat_stream(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    Returns tokens as they are generated instead of waiting for full response.
    """
    return StreamingResponse(
        stream_chat_response(request, background_tasks),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/health")
def chat_health():
    """Health check for chat service."""
    return {
        "status": "ok",
        "model": "gemini-2.5-flash (Vertex AI)",
        "tools_available": len(ALL_TOOLS),
        "rate_limit_handling": "exponential_backoff_max_6_retries",
    }


@router.get("/session/{session_id}")
def get_session(session_id: str):
    """Get session details for debugging/testing."""
    session = fs.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@router.get("/user/{user_id}/sessions")
def get_user_sessions(user_id: str, limit: int = 50):
    """
    Get session list for a user with titles for sidebar.
    Returns sessions sorted by most recent first.
    """
    try:
        # Query sessions for user (no order_by to avoid composite index requirement)
        sessions_query = fs.db.collection('sessions').where("user_id", "==", user_id).limit(limit * 2)  # Get extra to sort later
        sessions_docs = sessions_query.stream()
        
        session_list = []
        for doc in sessions_docs:
            session_data = doc.to_dict()
            session_id = doc.id
            
            # Get first user message for title
            messages = session_data.get("messages", [])
            title = "New Chat"
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    title = content[:40] + ("..." if len(content) > 40 else "")
                    break
            
            session_list.append({
                "session_id": session_id,
                "title": title,
                "created_at": session_data.get("created_at"),
                "status": session_data.get("status", "active")
            })
        
        # Sort by created_at in Python (most recent first)
        session_list.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        # Apply limit after sorting
        return session_list[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.delete("/session/{session_id}")
def delete_session(session_id: str, user_id: str):
    """
    Delete a session and all its associated data.
    Only the session owner can delete it.
    This does NOT affect RAG memories as those are cross-session.
    """
    try:
        # Get session to verify ownership
        session_ref = fs.db.collection('sessions').document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = session_doc.to_dict()
        if session_data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this session")
        
        # Delete the session document
        session_ref.delete()
        
        return {"status": "success", "message": f"Session {session_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
