/**
 * API client for backend communication.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper for API calls.
 */
export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Get session list for user.
 */
export async function getSessions(userId, limit = 50) {
  return apiRequest(`/chat/user/${userId}/sessions?limit=${limit}`);
}

/**
 * Get session details by ID.
 */
export async function getSession(sessionId) {
  return apiRequest(`/chat/session/${sessionId}`);
}

/**
 * Delete a session by ID.
 */
export async function deleteSession(sessionId, userId) {
  return apiRequest(`/chat/session/${sessionId}?user_id=${userId}`, {
    method: 'DELETE',
  });
}

export { API_BASE_URL };
