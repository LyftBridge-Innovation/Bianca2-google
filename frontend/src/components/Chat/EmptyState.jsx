import './EmptyState.css';

export function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-state-content">
        <h2 className="empty-state-title">Welcome to Bianca</h2>
        <p className="empty-state-subtitle">Your AI Chief of Staff</p>
        <div className="empty-state-suggestions">
          <p className="empty-state-prompt">Try asking me to:</p>
          <ul className="empty-state-list">
            <li>Check your calendar for upcoming meetings</li>
            <li>Send an email to someone</li>
            <li>Search your recent emails</li>
            <li>Create a calendar event</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
