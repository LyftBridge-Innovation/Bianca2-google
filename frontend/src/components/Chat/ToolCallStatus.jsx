import './ToolCallStatus.css';

const toolLabels = {
  list_upcoming_events: 'Checking your calendar...',
  create_calendar_event: 'Creating calendar event...',
  update_calendar_event: 'Updating calendar event...',
  delete_calendar_event: 'Deleting calendar event...',
  send_email: 'Sending email...',
  search_emails: 'Searching emails...',
  list_gmail_threads: 'Checking your inbox...',
  get_email_thread: 'Reading email...',
};

export function ToolCallStatus({ toolCall }) {
  if (!toolCall) return null;

  const label = toolLabels[toolCall.name] || `Using ${toolCall.name}...`;

  return (
    <div className="tool-call-status">
      <div className="tool-call-icon">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" opacity="0.3"/>
          <path d="M8 2 A6 6 0 0 1 14 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 8 8"
              to="360 8 8"
              dur="1s"
              repeatCount="indefinite"
            />
          </path>
        </svg>
      </div>
      <span className="tool-call-label">{label}</span>
    </div>
  );
}
