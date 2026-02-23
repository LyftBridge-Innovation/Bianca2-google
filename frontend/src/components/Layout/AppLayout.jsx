import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useChat } from '../../hooks/useChat';
import { Sidebar } from './Sidebar';
import { ChatWindow } from '../Chat/ChatWindow';
import './AppLayout.css';

export function AppLayout() {
  const { user } = useAuth();
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  
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

  // Load session when selection changes
  useEffect(() => {
    loadSession(selectedSessionId);
  }, [selectedSessionId, loadSession]);

  const handleSelectSession = async (sessionId) => {
    setSelectedSessionId(sessionId);
  };

  const handleNewChat = () => {
    setSelectedSessionId(null);
    clearMessages();
  };

  const handleSendMessage = async (message) => {
    await sendMessage(message);
  };

  return (
    <div className="app-layout">
      <Sidebar
        userId={user.userId}
        currentSessionId={sessionId || selectedSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
      />
      <ChatWindow
        messages={messages}
        isStreaming={isStreaming}
        currentToolCall={currentToolCall}
        streamingContent={streamingContent}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
