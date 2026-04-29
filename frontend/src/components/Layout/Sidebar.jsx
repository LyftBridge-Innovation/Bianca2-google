import { useSessions } from '../../hooks/useSessions';
import { Footer } from './Footer';
import './Sidebar.css';

export function Sidebar({
  userId,
  userPicture,
  userName,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onGoToConfig,
  onGoToMarketplace,
  activeView,
}) {
  const { sessions, loading, deleteSession } = useSessions(userId);

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation(); // Prevent triggering onSelectSession

    if (!confirm('Delete this chat? This cannot be undone.')) {
      return;
    }

    try {
      await deleteSession(sessionId);
      // If we deleted the current session, clear the chat
      if (sessionId === currentSessionId) {
        onNewChat();
      }
    } catch (err) {
      alert('Failed to delete session. Please try again.');
    }
  };

  const groupSessionsByDate = (sessions) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const grouped = {
      today: [],
      yesterday: [],
      previous7Days: [],
      older: [],
    };

    sessions.forEach((session) => {
      const sessionDate = new Date(session.created_at);
      const sessionDay = new Date(
        sessionDate.getFullYear(),
        sessionDate.getMonth(),
        sessionDate.getDate()
      );

      if (sessionDay.getTime() === today.getTime()) {
        grouped.today.push(session);
      } else if (sessionDay.getTime() === yesterday.getTime()) {
        grouped.yesterday.push(session);
      } else if (sessionDay >= sevenDaysAgo) {
        grouped.previous7Days.push(session);
      } else {
        grouped.older.push(session);
      }
    });

    return grouped;
  };

  const grouped = groupSessionsByDate(sessions);

  const renderSessionGroup = (title, sessions) => {
    if (sessions.length === 0) return null;

    return (
      <div className="sidebar-group" key={title}>
        <div className="sidebar-group-title">{title}</div>
        {sessions.map((session) => (
          <div
            key={session.session_id}
            className={`sidebar-session ${
              session.session_id === currentSessionId && activeView === 'chat' ? 'active' : ''
            }`}
          >
            <button
              className="sidebar-session-button"
              onClick={() => onSelectSession(session.session_id)}
            >
              <span className="sidebar-session-title">{session.title}</span>
            </button>
            <button
              className="sidebar-session-delete"
              onClick={(e) => handleDeleteSession(e, session.session_id)}
              title="Delete chat"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M4 4L12 12M12 4L4 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-logo">
          <img
            src={`${import.meta.env.BASE_URL}lyftbridge-favicon.png`}
            alt=""
            className="sidebar-logo-icon"
          />
          Bianca
        </h1>
        <button className="sidebar-new-chat" onClick={onNewChat}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              d="M10 4V16M4 10H16"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          New Chat
        </button>
      </div>

      <div className="sidebar-sessions">
        {loading ? (
          <div className="sidebar-loading">Loading sessions...</div>
        ) : (
          <>
            {renderSessionGroup('Today', grouped.today)}
            {renderSessionGroup('Yesterday', grouped.yesterday)}
            {renderSessionGroup('Previous 7 Days', grouped.previous7Days)}
            {renderSessionGroup('Older', grouped.older)}
          </>
        )}
      </div>

      {/* Footer — navigation buttons + branding */}
      <div className="sidebar-footer">
        <button
          className={`sidebar-config-btn ${activeView === 'marketplace' ? 'active' : ''}`}
          onClick={onGoToMarketplace}
        >
          <div className="sidebar-marketplace-icon">
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
              <path d="M2 5.5C2 4.4 2.9 3.5 4 3.5H16C17.1 3.5 18 4.4 18 5.5V7C18 7.8 17.5 8.4 16.8 8.7C16.9 9 17 9.3 17 9.6V15.5C17 16.6 16.1 17.5 15 17.5H5C3.9 17.5 3 16.6 3 15.5V9.6C3 9.3 3.1 9 3.2 8.7C2.5 8.4 2 7.8 2 7V5.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              <path d="M2 7H18M7 7V3.5M13 7V3.5M7 12H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="sidebar-config-label">Marketplace</span>
        </button>

        <button
          className={`sidebar-config-btn ${activeView === 'config' ? 'active' : ''}`}
          onClick={onGoToConfig}
        >
          {userPicture ? (
            <img src={userPicture} alt="" className="sidebar-config-avatar" referrerPolicy="no-referrer" />
          ) : (
            <div className="sidebar-config-avatar sidebar-config-avatar-fallback">
              {userName?.[0] || 'U'}
            </div>
          )}
          <span className="sidebar-config-label">Neural Config</span>
        </button>
      </div>
      <Footer className="sidebar-brand-footer" />
    </div>
  );
}
