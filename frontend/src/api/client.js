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

/**
 * Get required OAuth scopes from backend (built from YAML skill configs).
 */
export async function getRequiredScopes() {
  return apiRequest('/auth/scopes');
}

/**
 * List skills for a user.
 */
export async function getSkills(userId) {
  return apiRequest(`/skills/?user_id=${userId}`);
}

/**
 * Upload a skill markdown file.
 */
export async function uploadSkill(userId, filename, content) {
  return apiRequest('/skills/upload', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, filename, content }),
  });
}

/**
 * Delete a skill by ID.
 */
export async function deleteSkillAPI(skillId, userId) {
  return apiRequest(`/skills/${skillId}?user_id=${userId}`, {
    method: 'DELETE',
  });
}

/**
 * Publish a user's skill to the marketplace.
 */
export async function publishSkill(userId, skillId) {
  return apiRequest(`/skills/publish?user_id=${userId}&skill_id=${skillId}`, {
    method: 'POST',
  });
}

/**
 * Get all skills from the marketplace.
 */
export async function getMarketplaceSkills() {
  return apiRequest('/skills/marketplace');
}

/**
 * Install a skill from the marketplace to user's collection.
 */
export async function installFromMarketplace(userId, publicSkillId) {
  return apiRequest(
    `/skills/install-from-marketplace?user_id=${userId}&public_skill_id=${publicSkillId}`,
    { method: 'POST' }
  );
}

/**
 * Remove a skill from the marketplace (author only).
 */
export async function unpublishSkill(userId, publicSkillId) {
  return apiRequest(
    `/skills/unpublish/${publicSkillId}?user_id=${userId}`,
    { method: 'DELETE' }
  );
}

/**
 * Get all knowledge sections (persona, education, expertise, company).
 */
export async function getKnowledge() {
  return apiRequest('/config/knowledge');
}

/**
 * Save updated content to a specific knowledge file.
 */
export async function saveKnowledgeFile(category, filename, content) {
  return apiRequest(`/config/knowledge/${category}/${filename}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

/**
 * Get the current values list.
 */
export async function getValues() {
  return apiRequest('/config/values');
}

/**
 * Save an updated values list.
 */
export async function saveValues(values) {
  return apiRequest('/config/values', {
    method: 'PUT',
    body: JSON.stringify({ values }),
  });
}

/**
 * Get all config settings (identity, model, integrations).
 */
export async function getSettings() {
  return apiRequest('/config/settings');
}

/**
 * Update config settings (partial merge).
 */
export async function updateSettings(settings) {
  return apiRequest('/config/settings', {
    method: 'PUT',
    body: JSON.stringify({ settings }),
  });
}

/**
 * Get the fully assembled system prompt for preview.
 */
export async function getSystemPrompt() {
  return apiRequest('/config/system-prompt');
}

/**
 * Get education data (degrees and courses).
 */
export async function getEducation() {
  return apiRequest('/config/education');
}

/**
 * Save education data (degrees and courses).
 */
export async function saveEducation(degrees, courses) {
  return apiRequest('/config/education', {
    method: 'PUT',
    body: JSON.stringify({ degrees, courses }),
  });
}

// ── Task API ────────────────────────────────────────────────────────────────

/**
 * Create a new background task.
 */
export async function createTask(userId, taskType, parameters, sessionId = null) {
  return apiRequest('/tasks/', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      task_type: taskType,
      parameters,
      session_id: sessionId,
    }),
  });
}

/**
 * List tasks for a user.
 */
export async function getTasks(userId, status = null, limit = 50) {
  let url = `/tasks/?user_id=${userId}&limit=${limit}`;
  if (status) {
    url += `&status=${status}`;
  }
  return apiRequest(url);
}

/**
 * Get details of a specific task.
 */
export async function getTask(taskId, userId) {
  return apiRequest(`/tasks/${taskId}?user_id=${userId}`);
}

/**
 * Cancel a pending task.
 */
export async function cancelTask(taskId, userId) {
  return apiRequest(`/tasks/${taskId}/cancel?user_id=${userId}`, {
    method: 'POST',
  });
}

/**
 * Delete a completed or failed task.
 */
export async function deleteTaskAPI(taskId, userId) {
  return apiRequest(`/tasks/${taskId}?user_id=${userId}`, {
    method: 'DELETE',
  });
}

export { API_BASE_URL };
