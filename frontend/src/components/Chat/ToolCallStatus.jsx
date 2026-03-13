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
      <div className="tool-call-dot" />
      <span className="tool-call-label">{label}</span>
    </div>
  );
}
