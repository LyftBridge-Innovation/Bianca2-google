import { useSessions } from '../../hooks/useSessions';
import './Sidebar.css';

export function Sidebar({ userId, currentSessionId, onSelectSession, onNewChat }) {
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
              session.session_id === currentSessionId ? 'active' : ''
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
        <h1 className="sidebar-logo">Bianca</h1>
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
    </div>
  );
}
