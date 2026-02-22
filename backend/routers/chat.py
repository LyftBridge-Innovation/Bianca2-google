"""Chat endpoint for the AI Chief of Staff using Gemini + LangChain."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GOOGLE_API_KEY, TEST_USER_ID
from prompts import CHIEF_OF_STAFF_SYSTEM_PROMPT
from langchain_tools import ALL_TOOLS
from models import FirestoreCollections, Session, Message, ToolCall, ToolActionLog
from memory_utils import generate_human_readable
from summarization import summarize_session_sync
from memory_retrieval import retrieve_memories_for_message, format_memory_injection

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize Gemini LLM with tool calling
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.7,
).bind_tools(ALL_TOOLS)

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
        
        # Build message chain with system prompt and session history
        messages = [SystemMessage(content=CHIEF_OF_STAFF_SYSTEM_PROMPT)]
        
        # Add all messages from session history
        for msg in session.messages:
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
            original_system_prompt = CHIEF_OF_STAFF_SYSTEM_PROMPT
            enriched_system_prompt = f"{original_system_prompt}\n\n{memory_block}"
            messages[0] = SystemMessage(content=enriched_system_prompt)
            
            from logging import getLogger
            logger = getLogger(__name__)
            logger.info(f"Injected {memory_data['total_count']} memories (window: {memory_data['recency_window_days']} days)")
        # ────────────────────────────────────────────────────────────────────
        
        # Track tool calls for logging
        session_tool_calls = []
        
        # Invoke LLM with tools
        response = llm.invoke(messages)
        
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
                
                # Find and execute the tool
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
            response = llm.invoke(messages)
        
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


@router.get("/health")
def chat_health():
    """Health check for chat service."""
    return {
        "status": "ok",
        "model": "gemini-2.5-flash",
        "tools_available": len(ALL_TOOLS),
    }


@router.get("/session/{session_id}")
def get_session(session_id: str):
    """Get session details for debugging/testing."""
    session = fs.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@router.get("/user/{user_id}/sessions")
def get_user_sessions(user_id: str):
    """Get active session for a user."""
    session = fs.get_active_session_for_user(user_id)
    if not session:
        return {"active_session": None}
    return {"active_session": session.model_dump()}
