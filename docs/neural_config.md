Here's a complete breakdown of the Neural Config (Settings) section — everything it does and how it all works together:

Neural Config — Full Walkthrough
Neural Config is the central control panel for configuring your AI employee's identity, behavior, knowledge, and connections. It's organized into 9 tabs, each controlling a different aspect of the AI.

1. Persona Tab
This is where you define who the AI is — its identity, background, and personality.

AI Identity: Set the AI's first name, last name, phone number, email, voice (Shimmer, Nova, Alloy, etc.), and language preferences (primary + secondary language).
Knowledge sub-tab: Manage categorical knowledge entries across four buckets:
Role & Company — what the AI knows about its employer
Domain Knowledge — industry expertise
Personality — behavioral traits and tone
Style Guide — writing and communication style rules
There's also a Vocabulary section where you can import CSV files of terms and definitions the AI should understand.
Education sub-tab: Give the AI academic credentials — degrees (institution, level, field), courses (with codes and descriptions), and even course materials (detailed concepts/notes linked to specific courses).
Resume sub-tab: Professional experience entries — job titles, organizations, locations, date ranges, and descriptions of responsibilities. This all feeds into the AI's persona when it introduces itself or references its background.
2. Skills Tab
Controls what the AI can do — its functional capabilities.

Toggle individual skills on or off (the AI only uses enabled skills).
Create custom skills or upload Markdown (.md) files as new skills.
Skills can be file-based (loaded from the skills/ directory) or database-backed (created through the UI).
Each skill can declare which World Model categories it needs (Industry, Markets, Geography, Environment) — so when that skill activates, it automatically pulls in relevant business data.
There's a skill refresh button to clear the cache when you update skill files.
3. World Model Tab
Provides the AI with environmental and business context — the real-world data it uses for analysis and decision-making.

Four categories:

Industry & Competitive Landscape — competitors, market position, industry trends
Markets & Customer Segments — target audiences, market data
Geographic Context — regions, local regulations, demographics
Environmental Conditions — economic factors, seasonal patterns, etc.
Each entry supports different data types: plain text, URL/news sources (with metadata), toggles (yes/no facts), and selection lists. Skills can automatically pull from these categories when they're relevant to a task.

4. System Prompt & Model Tab
The AI's core brain configuration.

Model Selection: Choose which AI model to use (Gemini 2.0 Flash, Gemini 1.5 Pro, Claude 3.5 Sonnet). Changing this takes effect immediately — it clears the model cache and switches.
System Prompt: The master instruction set that governs all of the AI's behavior. This is the foundation that everything else builds on top of.
Temperature & Top-P sliders: Control how creative vs. deterministic the AI's responses are. Lower temperature = more predictable; higher = more creative.
5. Contacts Tab
A built-in CRM for managing the people the AI interacts with.

Add, edit, and delete contacts with: first/last name, email, phone, title, and preferred language.
Search and filter through the contact list.
The AI uses this to personalize interactions — when someone calls, texts, or emails, the AI looks them up to know who they are, their title, their preferred language, and their history.
Contact lookup works by both phone number and email.
6. Access Control Tab
Defines the AI's authority boundaries — what it's allowed and not allowed to do.

Authorizations: Explicit permissions for actions like sending emails, scheduling meetings, accessing files, or performing tasks autonomously.
Constraints: Hard rules like "Never discuss pricing without approval" or "Always CC a human on external emails." These act as guardrails that the AI checks before acting.
7. Values Tab
The AI's ethical and operational compass — core decision principles.

Define values like "Transparency," "Accuracy," "Professionalism," or custom ones specific to your business.
Set operational rules — specific do's and don'ts the AI must follow.
These are injected directly into the AI's system prompt, so they influence every interaction across all channels (SMS, email, voice).
Updating values immediately invalidates the cache so changes take effect on the next interaction.
8. Integrations & Templates Tab (Channels)
Configures how the AI communicates and connects with external services.

Voice Prompt: Customize the system instructions and opening greeting specifically for phone calls. Supports variables like {caller} for personalization.
Email Polling: Set how frequently the AI checks for new emails and which folders to monitor.
Templates: Manage standardized message templates for common scenarios.
Social Media:
LinkedIn — per-user and global integration, including automated posting workflows.
Instagram — configuration for automated posting.
Google OAuth Credentials: Manage Client ID and Secret for Drive, Calendar, and Gmail integrations.
Integration Status Dashboard: Shows live connection status for all channels — Voice (Twilio), SMS (Twilio), Email (Gmail/Outlook/Resend), and Google Workspace services.
9. Security Tab
Account and API safety.

Password Change: Update the dashboard login password.
API Keys & Secrets Status: A read-only view showing which sensitive keys are configured (Gemini, Twilio, OpenAI, Google, etc.). These are managed through environment secrets — the UI just shows whether they're present, never the actual values.
How It All Connects
All of these settings work together at runtime. When someone sends a message:

Contacts identify who's talking
Access Control checks if they're allowed to interact
The System Prompt + Values + World Model data combine into the AI's instruction set
Relevant Skills are loaded based on what the user is asking for
Persona knowledge, education, and resume shape the AI's identity in the response
The response goes out through the appropriate channel configured in Integrations
Every setting change (model, values, world model, skills) immediately invalidates the relevant cache so the AI picks up changes on the very next interaction — no restart needed.