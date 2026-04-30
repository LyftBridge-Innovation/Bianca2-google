import './EmptyState.css';

const CHIPS = [
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <rect x="3" y="3" width="14" height="14" rx="2" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M3 8h14M8 3v5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    label: 'Check my calendar',
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M3 5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5z" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M3 8l7 5 7-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    label: 'Triage my inbox',
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M4 4h8l4 4v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M12 4v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    label: 'Create a document',
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M10 6v4l3 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    label: 'Schedule a meeting',
  },
];

export function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-state-glow" aria-hidden="true" />

      <div className="empty-state-content">
        {/* Brand mark */}
        <img
          src={`${import.meta.env.BASE_URL}bianc-ai-avatar.png`}
          alt=""
          aria-hidden="true"
          className="empty-state-mark"
        />

        {/* Section badge */}
        <div className="section-badge empty-state-badge">
          <span className="section-badge__dot" />
          <span className="section-badge__label">AI Chief of Staff</span>
        </div>

        {/* Headline */}
        <h2 className="empty-state-title">
          What can I help<br />
          <span className="empty-state-title__gradient">with today?</span>
        </h2>

        <p className="empty-state-description">
          Ask me anything — I have full access to your Google Workspace.
        </p>

        {/* Feature chips */}
        <div className="empty-state-chips">
          {CHIPS.map(chip => (
            <div key={chip.label} className="empty-state-chip">
              <span className="empty-state-chip__icon">{chip.icon}</span>
              <span className="empty-state-chip__label">{chip.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
