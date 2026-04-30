import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Message.css';

export function Message({ message, isStreaming = false }) {
  const isUser = message.role === 'user';
  const [displayedContent, setDisplayedContent] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  // Typewriter effect for streaming assistant messages
  useEffect(() => {
    if (isStreaming && !isUser) {
      // Show content as it arrives (already has streaming effect from backend)
      setDisplayedContent(message.content);
    } else if (!isStreaming && !isUser && displayedContent !== message.content) {
      // Animate final message character by character
      if (currentIndex < message.content.length) {
        const timer = setTimeout(() => {
          setDisplayedContent(message.content.slice(0, currentIndex + 1));
          setCurrentIndex(currentIndex + 1);
        }, 10); // 10ms per character
        return () => clearTimeout(timer);
      }
    } else if (isUser) {
      // User messages appear instantly
      setDisplayedContent(message.content);
    }
  }, [message.content, isStreaming, isUser, currentIndex, displayedContent]);

  // Reset when message changes
  useEffect(() => {
    if (!isStreaming && !isUser) {
      setCurrentIndex(0);
      setDisplayedContent('');
    } else if (isUser) {
      setDisplayedContent(message.content);
    }
  }, [message, isStreaming, isUser]);

  if (isUser) {
    return (
      <div className="message message-user">
        <div className="message-content">
          {displayedContent}
        </div>
      </div>
    );
  }

  return (
    <div className="message message-assistant">
      <div className="message-assistant-inner">
        <img
          src={`${import.meta.env.BASE_URL}bianc-ai-avatar.png`}
          alt=""
          aria-hidden="true"
          className="message-avatar"
        />
        <div className="message-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{ a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}
          >
            {displayedContent}
          </ReactMarkdown>
          {isStreaming && <span className="typing-cursor">▊</span>}
        </div>
      </div>
    </div>
  );
}
