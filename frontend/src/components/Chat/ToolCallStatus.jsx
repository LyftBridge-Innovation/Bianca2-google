import './ToolCallStatus.css';

const TOOL_ICON = (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <circle cx="8" cy="8" r="6.5" stroke="white" strokeWidth="1.5"/>
    <path d="M8 5v3l2 1.5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const toolLabels = {
  list_upcoming_events:  'checking calendar',
  create_calendar_event: 'creating event',
  update_calendar_event: 'updating event',
  delete_calendar_event: 'removing event',
  send_email:            'sending email',
  draft_email_message:   'drafting email',
  send_email_message:    'sending email',
  search_emails:         'searching emails',
  list_gmail_threads:    'reading inbox',
  get_email_thread:      'reading email',
  list_drive_files:      'browsing drive',
  create_docx_document:  'creating document',
  create_xlsx_spreadsheet: 'building spreadsheet',
  create_pptx_presentation: 'building slides',
  create_pdf_document:   'creating pdf',
};

export function ToolCallStatus({ toolCall }) {
  if (!toolCall) return null;

  const label = toolLabels[toolCall.name] || toolCall.name.replace(/_/g, ' ');

  return (
    <div className="tool-call-status">
      <div className="tool-call-icon-wrap">{TOOL_ICON}</div>
      <span className="tool-call-label">{label}</span>
      <div className="tool-call-dot" />
    </div>
  );
}
