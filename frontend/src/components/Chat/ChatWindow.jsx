import { ChatInput } from './ChatInput';
import { MessageList } from './MessageList';
import './ChatWindow.css';

export function ChatWindow({ 
  messages, 
  isStreaming, 
  currentToolCall, 
  streamingContent,
  onSendMessage 
}) {
  return (
    <div className="chat-window">
      <MessageList 
        messages={messages}
        isStreaming={isStreaming}
        currentToolCall={currentToolCall}
        streamingContent={streamingContent}
      />
      <ChatInput 
        onSend={onSendMessage}
        disabled={isStreaming}
      />
    </div>
  );
}
