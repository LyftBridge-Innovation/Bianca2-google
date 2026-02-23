/**
 * useChat hook - handles SSE streaming with POST /chat/stream.
 * Uses fetch with ReadableStream (NOT EventSource which only supports GET).
 */
import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../api/client';

export function useChat(userId) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentToolCall, setCurrentToolCall] = useState(null);
  const [streamingContent, setStreamingContent] = useState('');
  const abortControllerRef = useRef(null);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isStreaming) return;

    // Add user message immediately
    const userMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    setIsStreaming(true);
    setStreamingContent('');
    setCurrentToolCall(null);

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          message: text,
          user_id: userId,
          session_id: sessionId,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedContent = ''; // Track content locally

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events in the buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('event:')) {
            // Event type - we infer this from data structure
            continue;
          }
          
          if (line.startsWith('data:')) {
            const dataStr = line.substring(5).trim();
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);

              // Handle different event types
              if (data.session_id && !sessionId) {
                // session event
                console.log('[SSE] Session created:', data.session_id);
                setSessionId(data.session_id);
              } else if (data.tool && data.status) {
                // tool_call event
                console.log('[SSE] Tool call:', data.tool);
                setCurrentToolCall(data.tool);
              } else if (data.token) {
                // token event
                accumulatedContent += data.token;
                setStreamingContent(accumulatedContent);
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }

      // Stream complete - add assistant message
      console.log('[SSE] Stream complete. Accumulated content length:', accumulatedContent.length);
      if (accumulatedContent) {
        const assistantMessage = {
          role: 'assistant',
          content: accumulatedContent,
          timestamp: new Date().toISOString(),
        };
        console.log('[SSE] Adding assistant message to UI');
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        console.warn('[SSE] No content accumulated during stream');
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Stream aborted');
      } else {
        console.error('Stream error:', error);
        // Add error message
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${error.message}`,
          timestamp: new Date().toISOString(),
        }]);
      }
    } finally {
      setIsStreaming(false);
      setCurrentToolCall(null);
      setStreamingContent('');
    }
  }, [userId, sessionId, isStreaming]);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setStreamingContent('');
    setCurrentToolCall(null);
  }, []);

  const loadSession = useCallback(async (sessionIdToLoad) => {
    if (!sessionIdToLoad) {
      clearMessages();
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat/session/${sessionIdToLoad}`);
      if (!response.ok) throw new Error('Failed to load session');
      
      const data = await response.json();
      setSessionId(sessionIdToLoad);
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  }, [clearMessages]);

  return {
    messages,
    sessionId,
    isStreaming,
    currentToolCall,
    streamingContent,
    sendMessage,
    stopStreaming,
    clearMessages,
    loadSession,
  };
}
