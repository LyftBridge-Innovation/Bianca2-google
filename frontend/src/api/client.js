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
 * Check whether the user's stored token is missing any required scopes.
 * Returns { needs_reauth: bool, missing_scopes: string[] }
 */
export async function checkNeedsReauth(userId) {
  return apiRequest(`/auth/needs-reauth/${userId}`);
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

/**
 * Retry a failed task.
 */
export async function retryTask(taskId, userId) {
  return apiRequest(`/tasks/${taskId}/retry?user_id=${userId}`, {
    method: 'POST',
  });
}

// ── Email Agent API ──────────────────────────────────────────────────────────

/**
 * Get the current email agent status for a user.
 * Returns { enabled, label_name, watch_expiry, watch_active, replied_count }
 */
export async function getEmailAgentStatus(userId) {
  return apiRequest(`/email-agent/status?user_id=${encodeURIComponent(userId)}`);
}

/**
 * Enable the email agent for a user with the given Gmail label name.
 * Returns { ok, label_name, label_id, watch_expiry }
 */
export async function enableEmailAgent(userId, labelName) {
  return apiRequest('/email-agent/enable', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, label_name: labelName }),
  });
}

/**
 * Disable the email agent for a user.
 */
export async function disableEmailAgent(userId) {
  return apiRequest('/email-agent/disable', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  });
}

// ── Phone number registration ────────────────────────────────────────────────

/**
 * Get the phone number registered for a user.
 * Returns { phone_number: string }
 */
export async function getPhoneNumber(userId) {
  return apiRequest(`/config/phone?user_id=${encodeURIComponent(userId)}`);
}

/**
 * Save (or clear) the phone number for a user.
 * phoneNumber should be in E.164 format, e.g. "+14155552671"
 */
export async function savePhoneNumber(userId, phoneNumber) {
  return apiRequest('/config/phone', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, phone_number: phoneNumber }),
  });
}

// ── Resume API ───────────────────────────────────────────────────────────────

/** Get security key status (boolean presence flags, no values). */
export async function getSecurityStatus() {
  return apiRequest('/config/security-status');
}

/** Get resume data (work experience). */
export async function getResume() {
  return apiRequest('/config/resume');
}

/** Save resume data (work experience). */
export async function saveResume(experience) {
  return apiRequest('/config/resume', {
    method: 'PUT',
    body: JSON.stringify({ experience }),
  });
}

// ── User Data API (contacts, world model, access control) ────────────────────

/** List all contacts for a user. */
export async function getContacts(userId) {
  return apiRequest(`/user-data/contacts?user_id=${encodeURIComponent(userId)}`);
}

/** Add a contact for a user. */
export async function addContact(userId, contact) {
  return apiRequest('/user-data/contacts', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, ...contact }),
  });
}

/** Delete a contact by ID. */
export async function deleteContact(userId, contactId) {
  return apiRequest(`/user-data/contacts/${contactId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

/** List all world model entries for a user. */
export async function getWorldModel(userId) {
  return apiRequest(`/user-data/world-model?user_id=${encodeURIComponent(userId)}`);
}

/** Add a world model entry for a user. */
export async function addWorldModelEntry(userId, entry) {
  return apiRequest('/user-data/world-model', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, ...entry }),
  });
}

/** Delete a world model entry by ID. */
export async function deleteWorldModelEntry(userId, entryId) {
  return apiRequest(`/user-data/world-model/${entryId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

/** Toggle enabled flag on a world model entry. */
export async function toggleWorldModelEntry(userId, entryId, enabled) {
  return apiRequest(
    `/user-data/world-model/${entryId}?user_id=${encodeURIComponent(userId)}&enabled=${enabled}`,
    { method: 'PATCH' }
  );
}

/** Get access control (authorizations + constraints) for a user. */
export async function getAccessControl(userId) {
  return apiRequest(`/user-data/access-control?user_id=${encodeURIComponent(userId)}`);
}

/** Save the full access control config for a user. */
export async function saveAccessControl(userId, authorizations, constraints) {
  return apiRequest('/user-data/access-control', {
    method: 'PUT',
    body: JSON.stringify({ user_id: userId, authorizations, constraints }),
  });
}

export { API_BASE_URL };
