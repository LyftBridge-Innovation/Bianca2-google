"""Utility functions for Phase 3 memory system."""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from config import GOOGLE_API_KEY, ASSISTANT_NAME


# Use cheapest model for human_readable generation
_cheap_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-8b",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.3,
)


def generate_human_readable(tool_name: str, parameters: dict, result: str) -> str:
    """
    Generate a human-readable description of a tool action.
    Uses a cheap LLM model for cost efficiency.
    
    Returns a sentence like: "Bianca declined a meeting with Sarah on Feb 19"
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
