import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useChat } from '../../hooks/useChat';
import { Sidebar } from './Sidebar';
import { ChatWindow } from '../Chat/ChatWindow';
import { NeuralConfig } from '../../pages/NeuralConfig';
import { Marketplace } from '../../pages/Marketplace';
import { checkNeedsReauth } from '../../api/client';
import './AppLayout.css';

export function AppLayout() {
  const { user, logout } = useAuth();
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'config' | 'marketplace'
  const [needsReauth, setNeedsReauth] = useState(false);

  const {
    messages,
    sessionId,
    isStreaming,
    currentToolCall,
    streamingContent,
    sendMessage,
    loadSession,
    clearMessages,
  } = useChat(user.userId);

  // Check on mount if the stored token is missing any newly required scopes
  useEffect(() => {
    checkNeedsReauth(user.userId)
      .then(data => { if (data.needs_reauth) setNeedsReauth(true); })
      .catch(() => {}); // silently ignore — don't block the app
  }, [user.userId]);

  // Load session when selection changes
  useEffect(() => {
    loadSession(selectedSessionId);
  }, [selectedSessionId, loadSession]);

  const handleSelectSession = async (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveView('chat');
  };

  const handleNewChat = () => {
    setSelectedSessionId(null);
    clearMessages();
    setActiveView('chat');
  };

  const handleSendMessage = async (message) => {
    await sendMessage(message);
  };

  const showSidebar = activeView !== 'config';

  return (
    <div className="app-layout">
      {needsReauth && (
        <div className="reauth-banner">
          <span className="reauth-banner__icon">⚠</span>
          <span className="reauth-banner__text">
            New permissions are required (e.g. Drive file upload for document creation).
          </span>
          <button
            className="reauth-banner__btn"
            onClick={() => { logout(); }}
          >
            Sign out &amp; re-authorise
          </button>
          <button
            className="reauth-banner__dismiss"
            onClick={() => setNeedsReauth(false)}
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}
      <div className="app-layout__inner">
        {showSidebar && (
          <Sidebar
            userId={user.userId}
            userPicture={user.picture}
            userName={user.name}
            currentSessionId={sessionId || selectedSessionId}
            onSelectSession={handleSelectSession}
            onNewChat={handleNewChat}
            onGoToConfig={() => setActiveView('config')}
            onGoToMarketplace={() => setActiveView('marketplace')}
            activeView={activeView}
          />
        )}
        {activeView === 'chat' ? (
          <ChatWindow
            messages={messages}
            isStreaming={isStreaming}
            currentToolCall={currentToolCall}
            streamingContent={streamingContent}
            onSendMessage={handleSendMessage}
          />
        ) : activeView === 'config' ? (
          <NeuralConfig onGoToChat={() => setActiveView('chat')} />
        ) : (
          <Marketplace onGoToChat={() => setActiveView('chat')} />
        )}
      </div>
    </div>
  );
}
