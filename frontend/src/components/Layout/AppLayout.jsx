import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useChat } from '../../hooks/useChat';
import { Sidebar } from './Sidebar';
import { ChatWindow } from '../Chat/ChatWindow';
import { NeuralConfig } from '../../pages/NeuralConfig';
import './AppLayout.css';

export function AppLayout() {
  const { user } = useAuth();
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'config'

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

  return (
    <div className="app-layout">
      <Sidebar
        userId={user.userId}
        userPicture={user.picture}
        userName={user.name}
        currentSessionId={sessionId || selectedSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onGoToConfig={() => setActiveView('config')}
        activeView={activeView}
      />
      {activeView === 'chat' ? (
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          currentToolCall={currentToolCall}
          streamingContent={streamingContent}
          onSendMessage={handleSendMessage}
        />
      ) : (
        <NeuralConfig onGoToChat={() => setActiveView('chat')} />
      )}
    </div>
  );
}
