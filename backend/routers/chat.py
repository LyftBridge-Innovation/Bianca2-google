"""Chat endpoint for the AI Chief of Staff using Gemini + LangChain."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GOOGLE_API_KEY
from prompts import CHIEF_OF_STAFF_SYSTEM_PROMPT
from langchain_tools import ALL_TOOLS

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize Gemini LLM with tool calling
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.7,
).bind_tools(ALL_TOOLS)

# ── Request/Response Models ───────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    history: list[ChatMessage]


# ── Chat Endpoint ─────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Accepts a user message and optional conversation history.
    Returns AI response with updated history.
    """
    try:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        # Build message chain with system prompt, history, and current message
        messages = [SystemMessage(content=CHIEF_OF_STAFF_SYSTEM_PROMPT)]
        
        # Add conversation history
        for msg in request.history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Add current user message
        messages.append(HumanMessage(content=request.message))
        
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
        # Handle both string and list content formats
        if isinstance(response.content, str):
            ai_response = response.content
        elif isinstance(response.content, list):
            # Extract text from content blocks
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            ai_response = " ".join(text_parts) if text_parts else "I've completed your request."
        else:
            ai_response = str(response.content)

        # Update history
        updated_history = request.history + [
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="assistant", content=ai_response),
        ]

        return ChatResponse(
            response=ai_response,
            history=updated_history,
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
