"""Utility functions for Phase 3 memory system."""
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage
from config import GCP_PROJECT_ID, GCP_LOCATION, ASSISTANT_NAME


# Use Vertex AI Gemini for human_readable generation (uses Google Cloud credits)
_cheap_llm = ChatVertexAI(
    model="gemini-2.5-flash",
    project=GCP_PROJECT_ID,
    location=GCP_LOCATION,
    temperature=0.3,
    max_retries=6,  # Retry with exponential backoff for rate limits
)


def generate_human_readable(tool_name: str, parameters: dict, result: str) -> str:
    """
    Generate a human-readable description of a tool action.
    Uses a cheap LLM model for cost efficiency.
    
    Returns a sentence like: "Bianc.ai declined a meeting with Sarah on Feb 19"
    """
    prompt = f"""Write one sentence describing what {ASSISTANT_NAME} just did, from the user's perspective.

Tool: {tool_name}
Parameters: {parameters}
Result: {result}

Requirements:
- Use past tense
- Start with "{ASSISTANT_NAME}"
- Keep it under 20 words
- Be specific with names and dates if available
- Do not include technical details

Example: "{ASSISTANT_NAME} declined a meeting with Sarah on Feb 19 and sent a notification"

Write only the sentence, nothing else:"""
    
    try:
        response = _cheap_llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        # Fallback to a simple format if LLM fails
        return f"{ASSISTANT_NAME} executed {tool_name}"
