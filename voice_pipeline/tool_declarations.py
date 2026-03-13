"""
Function declarations for Gemini Live tool calling.

All 9 custom tools (Gmail + Calendar) plus Google Search are declared here.
Passed to the Gemini Live session at connect time — cannot be added dynamically.
"""
from google.genai import types


def get_function_declarations() -> list[types.FunctionDeclaration]:
    """Returns all FunctionDeclaration objects for Gemini Live."""
    return [

        # ── Gmail ─────────────────────────────────────────────────────────────

        types.FunctionDeclaration(
            name="list_emails",
            description=(
                "List recent emails from the user's Gmail inbox. "
                "Use this when the user asks about their emails, inbox, or recent messages."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "max_results": types.Schema(
                        type=types.Type.INTEGER,
                        description="Maximum number of emails to return. Default is 10.",
                    ),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="get_email",
            description=(
                "Get the full content of a specific email by its ID. "
                "Use this after list_emails to read the full body of an email."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["email_id"],
                properties={
                    "email_id": types.Schema(
                        type=types.Type.STRING,
                        description="The Gmail message ID to retrieve.",
                    ),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="send_email",
            description=(
                "Send an email on behalf of the user. "
                "Only call this after the user has explicitly confirmed they want to send it."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["to", "subject", "body"],
                properties={
                    "to":      types.Schema(type=types.Type.STRING, description="Recipient email address."),
                    "subject": types.Schema(type=types.Type.STRING, description="Email subject line."),
                    "body":    types.Schema(type=types.Type.STRING, description="Email body text."),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="draft_email",
            description=(
                "Save an email as a draft without sending it. "
                "Use this as the default action when asked to compose an email, "
                "unless the user explicitly says to send it."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["to", "subject", "body"],
                properties={
                    "to":      types.Schema(type=types.Type.STRING, description="Recipient email address."),
                    "subject": types.Schema(type=types.Type.STRING, description="Email subject line."),
                    "body":    types.Schema(type=types.Type.STRING, description="Email body text."),
                },
            ),
        ),

        # ── Calendar ──────────────────────────────────────────────────────────

        types.FunctionDeclaration(
            name="list_events",
            description=(
                "List upcoming calendar events for the user. "
                "Use this when the user asks about their schedule, meetings, or calendar."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "days_ahead": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of days ahead to look for events. Default is 7.",
                    ),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="get_event",
            description=(
                "Get full details of a specific calendar event by its ID, "
                "including description, organizer, and all attendees."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["event_id"],
                properties={
                    "event_id": types.Schema(
                        type=types.Type.STRING,
                        description="The Google Calendar event ID to retrieve.",
                    ),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="create_event",
            description="Create a new calendar event for the user.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["title", "start", "end"],
                properties={
                    "title": types.Schema(type=types.Type.STRING, description="Event title."),
                    "start": types.Schema(
                        type=types.Type.STRING,
                        description="Start time in ISO 8601 format, e.g. 2024-01-15T10:00:00.",
                    ),
                    "end": types.Schema(
                        type=types.Type.STRING,
                        description="End time in ISO 8601 format, e.g. 2024-01-15T11:00:00.",
                    ),
                    "attendees": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="List of attendee email addresses.",
                    ),
                    "description": types.Schema(
                        type=types.Type.STRING,
                        description="Event description or notes.",
                    ),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="update_event",
            description=(
                "Update an existing calendar event. "
                "All fields except event_id are optional — only include what needs to change."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["event_id"],
                properties={
                    "event_id":    types.Schema(type=types.Type.STRING, description="The event ID to update."),
                    "title":       types.Schema(type=types.Type.STRING, description="New event title."),
                    "start":       types.Schema(type=types.Type.STRING, description="New start time in ISO 8601 format."),
                    "end":         types.Schema(type=types.Type.STRING, description="New end time in ISO 8601 format."),
                    "description": types.Schema(type=types.Type.STRING, description="New event description."),
                    "attendees": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Updated list of attendee email addresses.",
                    ),
                },
            ),
        ),

        types.FunctionDeclaration(
            name="decline_event",
            description="Decline a calendar event and notify the organizer.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                required=["event_id"],
                properties={
                    "event_id": types.Schema(type=types.Type.STRING, description="The event ID to decline."),
                    "message":  types.Schema(
                        type=types.Type.STRING,
                        description="Optional decline message to send to the organizer.",
                    ),
                },
            ),
        ),
    ]


def build_tools_config(enable_google_search: bool = True) -> list:
    """
    Returns the full tools list for the Gemini Live session config.
    Includes all custom function declarations and optionally Google Search.
    """
    custom_tool = types.Tool(function_declarations=get_function_declarations())

    if enable_google_search:
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        return [custom_tool, google_search_tool]

    return [custom_tool]
