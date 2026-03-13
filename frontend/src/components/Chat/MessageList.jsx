import { useRef, useEffect, useState } from 'react';
import { Message } from './Message';
import { TypingIndicator } from './TypingIndicator';
import { ToolCallStatus } from './ToolCallStatus';
import { EmptyState } from './EmptyState';
import './MessageList.css';

export function MessageList({ messages, isStreaming, currentToolCall, streamingContent }) {
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Check if user has scrolled away from bottom
  const handleScroll = () => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    setShouldAutoScroll(isNearBottom);
  };

  // Auto-scroll to bottom when new messages arrive or content is streaming
  useEffect(() => {
    if (shouldAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingContent, isStreaming, shouldAutoScroll]);

  return (
    <div 
      ref={containerRef}
      className="message-list" 
      onScroll={handleScroll}
    >
      {messages.length === 0 && !isStreaming ? (
        <EmptyState />
      ) : (
        <div className="message-list-inner">
          {messages.map((message, index) => (
            <Message key={index} message={message} />
          ))}
          
          {currentToolCall && (
            <ToolCallStatus toolCall={currentToolCall} />
          )}

          {isStreaming && streamingContent && (
            <Message 
              message={{ 
                role: 'assistant', 
                content: streamingContent 
              }}
              isStreaming={true}
            />
          )}

          {isStreaming && !streamingContent && !currentToolCall && (
            <TypingIndicator />
          )}
          
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
}
