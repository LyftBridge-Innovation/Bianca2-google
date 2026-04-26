import { useRef, useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Footer } from '../components/Layout/Footer';
import { useAuth } from '../hooks/useAuth';
import { useSkills } from '../hooks/useSkills';
import {
  publishSkill,
  getKnowledge,
  saveKnowledgeFile,
  getValues,
  saveValues,
  getSettings,
  updateSettings,
  getSystemPrompt,
  getEducation,
  saveEducation,
  getTasks,
  cancelTask,
  deleteTaskAPI,
  retryTask,
  getEmailAgentStatus,
  enableEmailAgent,
  disableEmailAgent,
  getPhoneNumber,
  savePhoneNumber,
  getSecurityStatus,
  getResume,
  saveResume,
  getContacts,
  addContact,
  deleteContact,
  getWorldModel,
  addWorldModelEntry,
  deleteWorldModelEntry,
  toggleWorldModelEntry,
  getAccessControl,
  saveAccessControl,
  API_BASE_URL,
} from '../api/client';
import './NeuralConfig.css';

const LOGO = import.meta.env.BASE_URL + 'lyftbridge.jpeg';

const VOICE_OPTIONS = [
  { id: 'Aoede', label: 'Aoede', desc: 'Warm female' },
  { id: 'Kore', label: 'Kore', desc: 'Bright female' },
  { id: 'Puck', label: 'Puck', desc: 'Expressive neutral' },
  { id: 'Charon', label: 'Charon', desc: 'Deep male' },
  { id: 'Fenrir', label: 'Fenrir', desc: 'Clear male' },
];

const MODEL_GROUPS = [
  {
    provider: 'Anthropic',
    color: '#c96442',
    models: [
      { id: 'claude-sonnet-4-6',          label: 'Claude Sonnet 4.6',  desc: 'Latest — most capable' },
      { id: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5',  desc: 'Best balance' },
      { id: 'claude-opus-4-6',            label: 'Claude Opus 4.6',    desc: 'Most powerful' },
      { id: 'claude-haiku-4-5-20251001',  label: 'Claude Haiku 4.5',   desc: 'Fast & cheap' },
    ],
  },
  {
    provider: 'Google Gemini',
    color: '#4dc8f5',
    models: [
      { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', desc: 'Fast & efficient' },
      { id: 'gemini-2.5-pro',   label: 'Gemini 2.5 Pro',   desc: 'Most capable Gemini' },
    ],
  },
];

const LANGUAGES = [
  'English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
  'Dutch', 'Russian', 'Japanese', 'Korean', 'Chinese', 'Arabic',
  'Hindi', 'Turkish', 'Polish', 'Swedish', 'Norwegian', 'Danish',
  'Finnish', 'Greek', 'Czech', 'Romanian', 'Hungarian', 'Thai',
  'Vietnamese', 'Indonesian', 'Malay', 'Hebrew', 'Ukrainian',
];

const WORLD_MODEL_CATEGORIES = [
  { id: 'industry', label: 'Industry' },
  { id: 'markets', label: 'Markets' },
  { id: 'geography', label: 'Geography' },
  { id: 'environment', label: 'Environment' },
];

const SECURITY_KEYS = [
  { key: 'google_api_key', label: 'Google / Gemini API Key' },
  { key: 'anthropic_api_key', label: 'Anthropic API Key' },
  { key: 'google_workspace_token', label: 'Google Workspace Token' },
  { key: 'twilio', label: 'Twilio (Voice/SMS)' },
];

export function NeuralConfig({ onGoToChat }) {
  const { user, logout } = useAuth();
  const { skills, loading, upload, deleteSkill } = useSkills(user.userId);
  const fileInputRef = useRef(null);
  const prevTaskStatusRef = useRef({});

  // ── Main tab state ─────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('persona');
  const [personaSubTab, setPersonaSubTab] = useState('identity');

  // ── Settings (shared by persona/identity, system prompt, integrations) ─────
  const [settings, setSettings] = useState(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);

  // ── Skills tab ─────────────────────────────────────────────────────────────
  const [publishingId, setPublishingId] = useState(null);

  // ── Persona / Knowledge sub-tab ────────────────────────────────────────────
  const [sections, setSections] = useState(null);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [editingFile, setEditingFile] = useState(null);
  const [editDraft, setEditDraft] = useState('');
  const [knowledgeSaving, setKnowledgeSaving] = useState(false);

  // ── Persona / Education sub-tab (local state) ──────────────────────────────
  const [degrees, setDegrees] = useState([]);
  const [courses, setCourses] = useState([]);
  const [showDegreeForm, setShowDegreeForm] = useState(false);
  const [showCourseForm, setShowCourseForm] = useState(false);

  // ── Persona / Resume sub-tab ───────────────────────────────────────────────
  const [experience, setExperience] = useState([]);
  const [showExpForm, setShowExpForm] = useState(false);
  const [resumeLoaded, setResumeLoaded] = useState(false);

  // ── Values tab ─────────────────────────────────────────────────────────────
  const [values, setValues] = useState(null);
  const [valuesLoading, setValuesLoading] = useState(false);
  const [editingPriority, setEditingPriority] = useState(null);
  const [valueDraft, setValueDraft] = useState({ title: '', rule: '' });
  const [valuesSaving, setValuesSaving] = useState(false);

  // ── System Prompt tab ──────────────────────────────────────────────────────
  const [promptPreview, setPromptPreview] = useState(null);
  const [promptLoading, setPromptLoading] = useState(false);

  // ── World Model tab ────────────────────────────────────────────────────────
  const [worldModelCat, setWorldModelCat] = useState('industry');
  const [worldModelEntries, setWorldModelEntries] = useState([]);
  const [showWMForm, setShowWMForm] = useState(false);
  const [worldModelLoaded, setWorldModelLoaded] = useState(false);

  // ── Contacts tab ───────────────────────────────────────────────────────────
  const [contacts, setContacts] = useState([]);
  const [contactSearch, setContactSearch] = useState('');
  const [showContactForm, setShowContactForm] = useState(false);
  const [contactsLoaded, setContactsLoaded] = useState(false);

  // ── Access Control tab ─────────────────────────────────────────────────────
  const [authorizations, setAuthorizations] = useState([]);
  const [constraints, setConstraints] = useState([]);
  const [authInput, setAuthInput] = useState('');
  const [constraintInput, setConstraintInput] = useState('');
  const [accessControlLoaded, setAccessControlLoaded] = useState(false);

  // ── Tasks tab ─────────────────────────────────────────────────────────────
  const [tasks, setTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [tasksFilter, setTasksFilter] = useState('all');
  const [tasksPage, setTasksPage] = useState(1);
  const TASKS_PER_PAGE = 10;

  // ── Security tab ───────────────────────────────────────────────────────────
  const [securityStatus, setSecurityStatus] = useState(null);

  // ── Email Agent tab ────────────────────────────────────────────────────────
  const [emailAgentStatus, setEmailAgentStatus] = useState(null);
  const [emailAgentLoading, setEmailAgentLoading] = useState(false);
  const [emailAgentLabelInput, setEmailAgentLabelInput] = useState('');
  const [emailAgentSaving, setEmailAgentSaving] = useState(false);

  // ── Phone number (Twilio voice) ────────────────────────────────────────────
  const [phoneNumber, setPhoneNumber] = useState('');
  const [phoneLoaded, setPhoneLoaded] = useState(false);
  const [phoneSaving, setPhoneSaving] = useState(false);

  // ── Toast notifications ─────────────────────────────────────────────────
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  };

  // ── Lazy-load data on tab visit ────────────────────────────────────────────
  useEffect(() => {
    const needsSettings = ['persona', 'prompt', 'integrations'].includes(activeTab);
    if (needsSettings && settings === null && !settingsLoading) {
      setSettingsLoading(true);
      getSettings()
        .then((data) => setSettings(data.settings))
        .catch((err) => alert(`Failed to load settings: ${err.message}`))
        .finally(() => setSettingsLoading(false));
    }
    if (activeTab === 'integrations' && emailAgentStatus === null && !emailAgentLoading) {
      setEmailAgentLoading(true);
      getEmailAgentStatus(user.userId)
        .then((data) => {
          setEmailAgentStatus(data);
          setEmailAgentLabelInput(data.label_name || '');
        })
        .catch(() => setEmailAgentStatus({ enabled: false, label_name: '', watch_active: false, replied_count: 0 }))
        .finally(() => setEmailAgentLoading(false));
    }
    if (activeTab === 'integrations' && !phoneLoaded) {
      setPhoneLoaded(true);
      getPhoneNumber(user.userId)
        .then((data) => setPhoneNumber(data.phone_number || ''))
        .catch(() => setPhoneNumber(''));
    }
  }, [activeTab, settings, settingsLoading, emailAgentStatus, emailAgentLoading, phoneLoaded]);

  // Load tasks when tasks tab is selected
  useEffect(() => {
    if (activeTab === 'tasks' && !tasksLoading && tasks.length === 0) {
      setTasksLoading(true);
      getTasks(user.userId)
        .then((data) => setTasks(data || []))
        .catch((err) => console.error('Failed to load tasks:', err))
        .finally(() => setTasksLoading(false));
    }
  }, [activeTab, user.userId]);

  // Refresh tasks with SSE when on tasks tab
  useEffect(() => {
    if (activeTab !== 'tasks') return;

    const eventSource = new EventSource(`${API_BASE_URL}/tasks/stream?user_id=${user.userId}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'connected' || data.type === 'keepalive') {
          // Connection established or keepalive
          return;
        }

        if (data.type === 'error') {
          console.error('SSE error:', data.message);
          return;
        }

        // Task update - merge into existing tasks
        setTasks((prevTasks) => {
          const existingIndex = prevTasks.findIndex((t) => t.task_id === data.task_id);
          if (existingIndex >= 0) {
            // Update existing task
            const updated = [...prevTasks];
            updated[existingIndex] = data;
            return updated;
          } else {
            // Add new task
            return [data, ...prevTasks];
          }
        });
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [activeTab, user.userId]);

  // Fire toast when a task transitions to completed or failed
  useEffect(() => {
    tasks.forEach((task) => {
      const prev = prevTaskStatusRef.current[task.task_id];
      if (prev && prev !== task.status && (task.status === 'completed' || task.status === 'failed')) {
        const name = task.task_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        if (task.status === 'completed') {
          addToast(`${name} completed`, 'completed');
        } else {
          addToast(`${name} failed: ${task.error || 'Unknown error'}`, 'failed');
        }
      }
      prevTaskStatusRef.current[task.task_id] = task.status;
    });
  }, [tasks]);

  // Reset to page 1 when filter changes
  useEffect(() => {
    setTasksPage(1);
  }, [tasksFilter]);

  useEffect(() => {
    if (activeTab === 'persona' && personaSubTab === 'knowledge' && sections === null && !knowledgeLoading) {
      setKnowledgeLoading(true);
      getKnowledge()
        .then((data) => setSections(data.sections))
        .catch((err) => alert(`Failed to load knowledge: ${err.message}`))
        .finally(() => setKnowledgeLoading(false));
    }
  }, [activeTab, personaSubTab, sections, knowledgeLoading]);

  useEffect(() => {
    if (activeTab === 'values' && values === null && !valuesLoading) {
      setValuesLoading(true);
      getValues()
        .then((data) => setValues(data.values))
        .catch((err) => alert(`Failed to load values: ${err.message}`))
        .finally(() => setValuesLoading(false));
    }
  }, [activeTab, values, valuesLoading]);

  useEffect(() => {
    if (activeTab === 'prompt' && promptPreview === null && !promptLoading) {
      setPromptLoading(true);
      getSystemPrompt()
        .then((data) => setPromptPreview(data))
        .catch((err) => alert(`Failed to load prompt: ${err.message}`))
        .finally(() => setPromptLoading(false));
    }
  }, [activeTab, promptPreview, promptLoading]);

  // ── Load education data when education sub-tab is selected ─────────────────
  const [educationLoaded, setEducationLoaded] = useState(false);
  useEffect(() => {
    if (activeTab === 'persona' && personaSubTab === 'education' && !educationLoaded) {
      setEducationLoaded(true);
      getEducation()
        .then((data) => {
          setDegrees(data.degrees || []);
          setCourses(data.courses || []);
        })
        .catch((err) => console.error('Failed to load education:', err));
    }
  }, [activeTab, personaSubTab, educationLoaded]);

  // ── Auto-save education data when it changes ───────────────────────────────
  const [educationSaveTimer, setEducationSaveTimer] = useState(null);
  useEffect(() => {
    if (!educationLoaded) return; // Don't save on initial load
    if (educationSaveTimer) clearTimeout(educationSaveTimer);
    const timer = setTimeout(() => {
      saveEducation(degrees, courses).catch((err) => console.error('Failed to save education:', err));
    }, 800);
    setEducationSaveTimer(timer);
    return () => clearTimeout(timer);
  }, [degrees, courses]);

  // ── Load security key status on tab visit ─────────────────────────────────
  useEffect(() => {
    if (activeTab === 'security' && securityStatus === null) {
      getSecurityStatus()
        .then((data) => setSecurityStatus(data))
        .catch(() => setSecurityStatus({}));
    }
  }, [activeTab, securityStatus]);

  // ── Load resume data when resume sub-tab is selected ──────────────────────
  useEffect(() => {
    if (activeTab === 'persona' && personaSubTab === 'resume' && !resumeLoaded) {
      setResumeLoaded(true);
      getResume()
        .then((data) => setExperience(data.experience || []))
        .catch((err) => console.error('Failed to load resume:', err));
    }
  }, [activeTab, personaSubTab, resumeLoaded]);

  // ── Auto-save resume when it changes ──────────────────────────────────────
  const [resumeSaveTimer, setResumeSaveTimer] = useState(null);
  useEffect(() => {
    if (!resumeLoaded) return;
    if (resumeSaveTimer) clearTimeout(resumeSaveTimer);
    const timer = setTimeout(() => {
      saveResume(experience).catch((err) => console.error('Failed to save resume:', err));
    }, 800);
    setResumeSaveTimer(timer);
    return () => clearTimeout(timer);
  }, [experience]);

  // ── Load contacts on tab visit ─────────────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'contacts' && !contactsLoaded) {
      setContactsLoaded(true);
      getContacts(user.userId)
        .then((data) => setContacts(data.contacts || []))
        .catch((err) => console.error('Failed to load contacts:', err));
    }
  }, [activeTab, contactsLoaded]);

  // ── Load world model on tab visit ──────────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'worldmodel' && !worldModelLoaded) {
      setWorldModelLoaded(true);
      getWorldModel(user.userId)
        .then((data) => setWorldModelEntries(data.entries || []))
        .catch((err) => console.error('Failed to load world model:', err));
    }
  }, [activeTab, worldModelLoaded]);

  // ── Load access control on tab visit ──────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'access' && !accessControlLoaded) {
      setAccessControlLoaded(true);
      getAccessControl(user.userId)
        .then((data) => {
          setAuthorizations(data.authorizations || []);
          setConstraints(data.constraints || []);
        })
        .catch((err) => console.error('Failed to load access control:', err));
    }
  }, [activeTab, accessControlLoaded]);

  // ── Settings handlers ──────────────────────────────────────────────────────
  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSettingsDirty(true);
  };

  const saveSettingsHandler = async () => {
    setSettingsSaving(true);
    try {
      await updateSettings(settings);
      setSettingsDirty(false);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSettingsSaving(false);
    }
  };

  // ── Skills handlers ────────────────────────────────────────────────────────
  const handlePublish = async (skillId) => {
    if (!confirm('Publish this skill to the marketplace?')) return;
    setPublishingId(skillId);
    try {
      await publishSkill(user.userId, skillId);
      alert('Skill published!');
    } catch (err) {
      alert(`Publish failed: ${err.message}`);
    } finally {
      setPublishingId(null);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try { await upload(file); } catch (err) { alert(`Upload failed: ${err.message}`); }
    e.target.value = '';
  };

  const handleDeleteSkill = async (skillId, filename) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    try { await deleteSkill(skillId); } catch (err) { alert(`Delete failed: ${err.message}`); }
  };

  // ── Knowledge handlers ─────────────────────────────────────────────────────
  const startEditFile = (category, filename, content) => {
    if (editingFile && !confirm('Discard unsaved changes?')) return;
    setEditingFile({ category, filename });
    setEditDraft(content);
  };

  const cancelEditFile = () => { setEditingFile(null); setEditDraft(''); };

  const saveFile = async () => {
    setKnowledgeSaving(true);
    try {
      await saveKnowledgeFile(editingFile.category, editingFile.filename, editDraft);
      setSections((prev) =>
        prev.map((s) =>
          s.category !== editingFile.category ? s : {
            ...s, files: s.files.map((f) =>
              f.filename !== editingFile.filename ? f : { ...f, content: editDraft }
            ),
          }
        )
      );
      setEditingFile(null);
      setEditDraft('');
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setKnowledgeSaving(false);
    }
  };

  // ── Values handlers ────────────────────────────────────────────────────────
  const startEditValue = (v) => {
    if (editingPriority !== null && !confirm('Discard unsaved changes?')) return;
    setEditingPriority(v.priority);
    setValueDraft({ title: v.title, rule: v.rule });
  };

  const cancelEditValue = () => { setEditingPriority(null); setValueDraft({ title: '', rule: '' }); };

  const saveValue = async () => {
    setValuesSaving(true);
    const updated = values.map((v) =>
      v.priority === editingPriority ? { ...v, title: valueDraft.title, rule: valueDraft.rule } : v
    );
    try {
      await saveValues(updated);
      setValues(updated);
      setEditingPriority(null);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setValuesSaving(false);
    }
  };

  // ── System Prompt handlers ─────────────────────────────────────────────────
  const refreshPrompt = () => {
    setPromptLoading(true);
    getSystemPrompt()
      .then((data) => setPromptPreview(data))
      .catch((err) => alert(`Failed to refresh: ${err.message}`))
      .finally(() => setPromptLoading(false));
  };

  // ── Task handlers ─────────────────────────────────────────────────────────
  const handleCancelTask = async (taskId) => {
    try {
      await cancelTask(taskId, user.userId);
      setTasks(tasks.map((t) => t.task_id === taskId ? { ...t, status: 'failed', error: 'Cancelled by user' } : t));
    } catch (err) {
      alert(`Failed to cancel: ${err.message}`);
    }
  };

  const handleDeleteTask = async (taskId) => {
    try {
      await deleteTaskAPI(taskId, user.userId);
      setTasks(tasks.filter((t) => t.task_id !== taskId));
    } catch (err) {
      alert(`Failed to delete: ${err.message}`);
    }
  };

  const handleRetryTask = async (taskId) => {
    try {
      const updated = await retryTask(taskId, user.userId);
      setTasks(tasks.map((t) => t.task_id === taskId ? updated : t));
    } catch (err) {
      alert(`Failed to retry: ${err.message}`);
    }
  };

  const handleExportTasks = () => {
    const blob = new Blob([JSON.stringify(tasks, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bianca-tasks-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredTasks = tasks.filter((t) => {
    if (tasksFilter === 'all') return true;
    return t.status === tasksFilter;
  });

  const totalTaskPages = Math.ceil(filteredTasks.length / TASKS_PER_PAGE);
  const paginatedTasks = filteredTasks.slice((tasksPage - 1) * TASKS_PER_PAGE, tasksPage * TASKS_PER_PAGE);
  const activeTasksCount = tasks.filter((t) => t.status === 'pending' || t.status === 'running').length;

  const getTaskIcon = (type) => {
    switch (type) {
      case 'create_doc':
        return (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M3 2h7l3 3v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.3"/>
            <path d="M10 2v3h3M5 8h6M5 11h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
        );
      case 'send_email':
      case 'draft_email':
        return (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <rect x="1.5" y="3.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
            <path d="M1.5 5.5l6.5 4.5 6.5-4.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
        );
      case 'create_slides':
        return (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
            <path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
        );
      case 'create_sheet':
        return (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <rect x="1.5" y="1.5" width="13" height="13" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
            <path d="M1.5 6h13M1.5 10h13M6 1.5v13" stroke="currentColor" strokeWidth="1.3"/>
          </svg>
        );
      default:
        return (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3"/>
            <path d="M8 5v3l2 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
        );
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return '#f59e0b';
      case 'running': return '#3b82f6';
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const formatTimeAgo = (iso) => {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  // ── Utils ──────────────────────────────────────────────────────────────────
  const formatDate = (iso) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const formatSize = (b) => b < 1024 ? `${b} B` : `${(b / 1024).toFixed(1)} KB`;

  // ── Contact handlers ───────────────────────────────────────────────────────
  const handleAddContact = async (contact) => {
    try {
      const res = await addContact(user.userId, contact);
      setContacts((prev) => [...prev, { id: res.id, ...contact }]);
      setShowContactForm(false);
    } catch (err) {
      addToast(`Failed to add contact: ${err.message}`, 'failed');
    }
  };

  const handleDeleteContact = async (contactId, index) => {
    try {
      await deleteContact(user.userId, contactId);
      setContacts((prev) => prev.filter((_, j) => j !== index));
    } catch (err) {
      addToast(`Failed to delete contact: ${err.message}`, 'failed');
    }
  };

  // ── World model handlers ───────────────────────────────────────────────────
  const handleAddWorldModelEntry = async (entry) => {
    try {
      const res = await addWorldModelEntry(user.userId, entry);
      setWorldModelEntries((prev) => [...prev, { id: res.id, ...entry }]);
      setShowWMForm(false);
    } catch (err) {
      addToast(`Failed to add entry: ${err.message}`, 'failed');
    }
  };

  const handleDeleteWorldModelEntry = async (entryId, index) => {
    try {
      await deleteWorldModelEntry(user.userId, entryId);
      setWorldModelEntries((prev) => prev.filter((_, j) => j !== index));
    } catch (err) {
      addToast(`Failed to delete entry: ${err.message}`, 'failed');
    }
  };

  const handleToggleWorldModelEntry = async (entry, index) => {
    const newEnabled = !entry.enabled;
    setWorldModelEntries((prev) => prev.map((x, j) => j === index ? { ...x, enabled: newEnabled } : x));
    try {
      await toggleWorldModelEntry(user.userId, entry.id, newEnabled);
    } catch (err) {
      // revert on failure
      setWorldModelEntries((prev) => prev.map((x, j) => j === index ? { ...x, enabled: !newEnabled } : x));
      addToast(`Failed to toggle entry: ${err.message}`, 'failed');
    }
  };

  // ── Access control handlers ────────────────────────────────────────────────
  const persistAccessControl = async (newAuth, newConstraints) => {
    try {
      await saveAccessControl(user.userId, newAuth, newConstraints);
    } catch (err) {
      addToast(`Failed to save access control: ${err.message}`, 'failed');
    }
  };

  const handleAddAuthorization = () => {
    if (!authInput.trim()) return;
    const updated = [...authorizations, authInput.trim()];
    setAuthorizations(updated);
    setAuthInput('');
    persistAccessControl(updated, constraints);
  };

  const handleDeleteAuthorization = (index) => {
    const updated = authorizations.filter((_, j) => j !== index);
    setAuthorizations(updated);
    persistAccessControl(updated, constraints);
  };

  const handleAddConstraint = () => {
    if (!constraintInput.trim()) return;
    const updated = [...constraints, constraintInput.trim()];
    setConstraints(updated);
    setConstraintInput('');
    persistAccessControl(authorizations, updated);
  };

  const handleDeleteConstraint = (index) => {
    const updated = constraints.filter((_, j) => j !== index);
    setConstraints(updated);
    persistAccessControl(authorizations, updated);
  };

  const filteredContacts = contacts.filter((c) => {
    if (!contactSearch.trim()) return true;
    const q = contactSearch.toLowerCase();
    return (c.firstName + ' ' + c.lastName).toLowerCase().includes(q) ||
           c.email?.toLowerCase().includes(q) || c.title?.toLowerCase().includes(q);
  });

  const filteredWorldModel = worldModelEntries.filter((e) => e.category === worldModelCat);

  // ── Tab definitions ────────────────────────────────────────────────────────
  const tabs = [
    { id: 'persona', label: 'Persona', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="7" r="3.5" stroke="currentColor" strokeWidth="1.3"/><path d="M3 16c0-3 2.7-5 6-5s6 2 6 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg> },
    { id: 'skills', label: 'Skills', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><rect x="3" y="2" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M6 6H12M6 9H11M6 12H9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg> },
    { id: 'worldmodel', label: 'World Model', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.3"/><path d="M3 9h12M9 3c-2 2-2 10 0 12M9 3c2 2 2 10 0 12" stroke="currentColor" strokeWidth="1.1"/></svg> },
    { id: 'prompt', label: 'System Prompt', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><path d="M4 4h10v10H4z" stroke="currentColor" strokeWidth="1.3" rx="1"/><path d="M7 8l2 2-2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/><path d="M11 12h2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg> },
    { id: 'contacts', label: 'Contacts', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><rect x="3" y="2" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><circle cx="9" cy="7" r="2" stroke="currentColor" strokeWidth="1.1"/><path d="M6 13c0-1.5 1.3-2.5 3-2.5s3 1 3 2.5" stroke="currentColor" strokeWidth="1.1"/></svg> },
    { id: 'access', label: 'Access Control', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><rect x="4" y="8" width="10" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M6 8V5.5a3 3 0 016 0V8" stroke="currentColor" strokeWidth="1.3"/></svg> },
    { id: 'values', label: 'Values', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><path d="M9 2L10.8 6.8L16 7.2L12.2 10.6L13.4 15.6L9 13L4.6 15.6L5.8 10.6L2 7.2L7.2 6.8L9 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></svg> },
    { id: 'integrations', label: 'Integrations', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="2" stroke="currentColor" strokeWidth="1.3"/><path d="M9 2v3M9 13v3M2 9h3M13 9h3M4.2 4.2l2.1 2.1M11.7 11.7l2.1 2.1M4.2 13.8l2.1-2.1M11.7 6.3l2.1-2.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg> },
    { id: 'tasks', label: 'Tasks', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><rect x="3" y="3" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.3"/><path d="M6 9l2 2 4-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg> },
    { id: 'security', label: 'Security', icon: <svg width="14" height="14" viewBox="0 0 18 18" fill="none"><path d="M9 2L3 5v4c0 4 2.5 6.5 6 8 3.5-1.5 6-4 6-8V5L9 2z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><path d="M7 9l2 2 3-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg> },
  ];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="neural-config">
      {/* Header */}
      <div className="nc-header">
        <div className="nc-header-left">
          <img src={LOGO} alt="Lyftbridge" className="nc-header-logo" />
          <h1 className="nc-title">Neural Config</h1>
        </div>
        <button className="nc-back-btn" onClick={onGoToChat}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M11 4L6 9L11 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Back to Chat
        </button>
      </div>

      {/* Profile Card */}
      <section className="nc-section">
        <div className="nc-profile-card">
          <div className="nc-avatar-wrapper">
            {user.picture ? (
              <img src={user.picture} alt={user.name} className="nc-avatar" referrerPolicy="no-referrer" />
            ) : (
              <div className="nc-avatar nc-avatar-fallback">{user.name?.[0] || 'U'}</div>
            )}
          </div>
          <div className="nc-profile-info">
            <div className="nc-profile-name">{user.name}</div>
            <div className="nc-profile-email">{user.email}</div>
          </div>
          <button className="nc-logout-btn" onClick={logout}>Sign out</button>
        </div>
      </section>

      {/* Tab Bar */}
      <div className="nc-tabs">
        {tabs.map((t) => (
          <button key={t.id} className={`nc-tab${activeTab === t.id ? ' active' : ''}`} onClick={() => setActiveTab(t.id)}>
            <span className="nc-tab-icon">{t.icon}</span>
            {t.label}
            {t.id === 'tasks' && activeTasksCount > 0 && (
              <span className="nc-tab-badge">{activeTasksCount}</span>
            )}
          </button>
        ))}
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* PERSONA TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'persona' && (
        <section className="nc-section">
          <div className="nc-subtabs">
            {['identity', 'knowledge', 'education', 'resume'].map((st) => (
              <button key={st} className={`nc-subtab${personaSubTab === st ? ' active' : ''}`}
                onClick={() => setPersonaSubTab(st)}>
                {st.charAt(0).toUpperCase() + st.slice(1)}
              </button>
            ))}
          </div>

          {/* Identity Sub-Tab */}
          {personaSubTab === 'identity' && (
            <>
              <h2 className="nc-section-title">AI Identity</h2>
              <p className="nc-section-desc">Core identity fields that define who Bianca is.</p>
              {settingsLoading || !settings ? <div className="nc-loading">Loading...</div> : (
                <div className="nc-knowledge-section">
                  <div className="nc-knowledge-body">
                    <div className="nc-form-grid">
                      <div className="nc-form-group">
                        <label className="nc-form-label">Name</label>
                        <input className="nc-form-input" value={settings.ai_name || ''} onChange={(e) => updateSetting('ai_name', e.target.value)} />
                      </div>
                      <div className="nc-form-group">
                        <label className="nc-form-label">Role</label>
                        <input className="nc-form-input" value={settings.ai_role || ''} onChange={(e) => updateSetting('ai_role', e.target.value)} />
                      </div>
                      <div className="nc-form-group">
                        <label className="nc-form-label">Primary Language</label>
                        <select className="nc-form-select" value={settings.primary_language || 'English'} onChange={(e) => updateSetting('primary_language', e.target.value)}>
                          {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
                        </select>
                      </div>
                      <div className="nc-form-group">
                        <label className="nc-form-label">Secondary Language</label>
                        <select className="nc-form-select" value={settings.secondary_language || ''} onChange={(e) => updateSetting('secondary_language', e.target.value)}>
                          <option value="">None</option>
                          {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
                        </select>
                      </div>
                      <div className="nc-form-group full-width">
                        <label className="nc-form-label">Voice</label>
                        <div className="nc-voice-options">
                          {VOICE_OPTIONS.map((v) => (
                            <button key={v.id} className={`nc-voice-chip${settings.ai_voice === v.id ? ' active' : ''}`}
                              onClick={() => updateSetting('ai_voice', v.id)} title={v.desc}>{v.label}</button>
                          ))}
                        </div>
                      </div>
                      {settingsDirty && (
                        <div className="nc-form-actions">
                          <button className="nc-save-btn" onClick={saveSettingsHandler} disabled={settingsSaving}>
                            {settingsSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Knowledge Sub-Tab */}
          {personaSubTab === 'knowledge' && (
            <>
              <h2 className="nc-section-title">Knowledge Base</h2>
              <p className="nc-section-desc">Files that shape Bianca's identity, expertise, and context.</p>
              {knowledgeLoading ? <div className="nc-loading">Loading...</div> : sections === null ? null : (
                sections.map((section) => section.files.map((file) => {
                  const isEditing = editingFile?.category === section.category && editingFile?.filename === file.filename;
                  return (
                    <div key={`${section.category}/${file.filename}`} className="nc-knowledge-section">
                      <div className="nc-knowledge-header">
                        <span className="nc-knowledge-label">{section.label}</span>
                        {!isEditing && (
                          <button className="nc-edit-trigger-btn" onClick={() => startEditFile(section.category, file.filename, file.content)}>
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M11.5 2.5L13.5 4.5L5 13H3V11L11.5 2.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/></svg>
                            Edit
                          </button>
                        )}
                      </div>
                      <div className="nc-knowledge-body">
                        {isEditing ? (
                          <>
                            <textarea className="nc-knowledge-textarea" value={editDraft} onChange={(e) => setEditDraft(e.target.value)} autoFocus />
                            <div className="nc-edit-actions">
                              <button className="nc-cancel-btn" onClick={cancelEditFile}>Cancel</button>
                              <button className="nc-save-btn" onClick={saveFile} disabled={knowledgeSaving}>{knowledgeSaving ? 'Saving...' : 'Save'}</button>
                            </div>
                          </>
                        ) : (
                          <div className="nc-knowledge-text"><ReactMarkdown remarkPlugins={[remarkGfm]}>{file.content}</ReactMarkdown></div>
                        )}
                      </div>
                    </div>
                  );
                }))
              )}
            </>
          )}

          {/* Education Sub-Tab */}
          {personaSubTab === 'education' && (
            <>
              <h2 className="nc-section-title">Education & Training</h2>
              <p className="nc-section-desc">Academic credentials and training that shape the AI's background.</p>

              <div className="nc-edu-section">
                <div className="nc-edu-header">
                  <span className="nc-edu-title">Degrees</span>
                </div>
                {degrees.length === 0 ? (
                  <div className="nc-empty-state">
                    <div className="nc-empty-state-text">No degrees added yet</div>
                    <div className="nc-empty-state-hint">Add academic credentials to shape the AI's educational background</div>
                  </div>
                ) : (
                  <div className="nc-edu-list">
                    {degrees.map((d, i) => (
                      <div key={i} className="nc-edu-card">
                        <div className="nc-edu-card-header">
                          <span className="nc-edu-card-name">{d.name}</span>
                          <span className="nc-edu-card-level">{d.level}</span>
                        </div>
                        <div className="nc-edu-card-institution">{d.institution}</div>
                        <div className="nc-edu-card-field">{d.field}</div>
                        <div className="nc-edu-card-actions">
                          <button className="nc-contact-delete" onClick={() => setDegrees(degrees.filter((_, j) => j !== i))}>Delete</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <button className="nc-add-entry-btn" onClick={() => setShowDegreeForm(!showDegreeForm)}>
                  {showDegreeForm ? 'Cancel' : '+ Add Degree'}
                </button>
                {showDegreeForm && (
                  <div className="nc-add-form">
                    <div className="nc-add-form-title">Add Degree</div>
                    <div className="nc-add-form-grid">
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Degree Name</label><input className="nc-add-form-input" placeholder="e.g. Bachelor of Science" id="deg-name" /></div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Level</label>
                        <select className="nc-add-form-select" id="deg-level"><option>Bachelors</option><option>Masters</option><option>Doctorate</option><option>Certificate</option></select>
                      </div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Institution</label><input className="nc-add-form-input" placeholder="University name" id="deg-inst" /></div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Field</label><input className="nc-add-form-input" placeholder="e.g. Computer Science" id="deg-field" /></div>
                      <div className="nc-add-form-actions">
                        <button className="nc-cancel-btn" onClick={() => setShowDegreeForm(false)}>Cancel</button>
                        <button className="nc-save-btn" onClick={() => {
                          const name = document.getElementById('deg-name').value;
                          const level = document.getElementById('deg-level').value;
                          const inst = document.getElementById('deg-inst').value;
                          const field = document.getElementById('deg-field').value;
                          if (name) { setDegrees([...degrees, { name, level, institution: inst, field }]); setShowDegreeForm(false); }
                        }}>Add</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="nc-edu-section">
                <div className="nc-edu-header"><span className="nc-edu-title">Courses</span></div>
                {courses.length === 0 ? (
                  <div className="nc-empty-state"><div className="nc-empty-state-text">No courses added yet</div></div>
                ) : (
                  <div className="nc-edu-list">
                    {courses.map((c, i) => (
                      <div key={i} className="nc-edu-card">
                        <div className="nc-edu-card-header"><span className="nc-edu-card-name">{c.code} - {c.name}</span></div>
                        <div className="nc-edu-card-field">{c.description}</div>
                        <div className="nc-edu-card-actions"><button className="nc-contact-delete" onClick={() => setCourses(courses.filter((_, j) => j !== i))}>Delete</button></div>
                      </div>
                    ))}
                  </div>
                )}
                <button className="nc-add-entry-btn" onClick={() => setShowCourseForm(!showCourseForm)}>{showCourseForm ? 'Cancel' : '+ Add Course'}</button>
                {showCourseForm && (
                  <div className="nc-add-form">
                    <div className="nc-add-form-title">Add Course</div>
                    <div className="nc-add-form-grid">
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Course Code</label><input className="nc-add-form-input" placeholder="e.g. CS101" id="course-code" /></div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Course Name</label><input className="nc-add-form-input" placeholder="e.g. Intro to AI" id="course-name" /></div>
                      <div className="nc-add-form-group full"><label className="nc-add-form-label">Description</label><textarea className="nc-add-form-textarea" placeholder="Course description..." id="course-desc" /></div>
                      <div className="nc-add-form-actions">
                        <button className="nc-cancel-btn" onClick={() => setShowCourseForm(false)}>Cancel</button>
                        <button className="nc-save-btn" onClick={() => {
                          const code = document.getElementById('course-code').value;
                          const name = document.getElementById('course-name').value;
                          const desc = document.getElementById('course-desc').value;
                          if (code && name) { setCourses([...courses, { code, name, description: desc }]); setShowCourseForm(false); }
                        }}>Add</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Resume Sub-Tab */}
          {personaSubTab === 'resume' && (
            <>
              <h2 className="nc-section-title">Resume & Experience</h2>
              <p className="nc-section-desc">Professional background that shapes the AI's expertise.</p>

              <div className="nc-resume-section">
                <div className="nc-resume-header"><span className="nc-resume-title">Work Experience</span></div>
                {experience.length === 0 ? (
                  <div className="nc-empty-state"><div className="nc-empty-state-text">No experience entries yet</div></div>
                ) : (
                  <div className="nc-resume-list">
                    {experience.map((e, i) => (
                      <div key={i} className="nc-resume-card">
                        <div className="nc-resume-card-header">
                          <span className="nc-resume-card-title">{e.title}</span>
                          <span className="nc-resume-card-dates">{e.startDate} - {e.endDate || 'Present'}</span>
                        </div>
                        <div className="nc-resume-card-org">{e.organization}</div>
                        <div className="nc-resume-card-desc">{e.description}</div>
                        <div className="nc-resume-card-actions"><button className="nc-contact-delete" onClick={() => setExperience(experience.filter((_, j) => j !== i))}>Delete</button></div>
                      </div>
                    ))}
                  </div>
                )}
                <button className="nc-add-entry-btn" onClick={() => setShowExpForm(!showExpForm)}>{showExpForm ? 'Cancel' : '+ Add Experience'}</button>
                {showExpForm && (
                  <div className="nc-add-form">
                    <div className="nc-add-form-title">Add Experience</div>
                    <div className="nc-add-form-grid">
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Job Title</label><input className="nc-add-form-input" placeholder="e.g. Senior Engineer" id="exp-title" /></div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Organization</label><input className="nc-add-form-input" placeholder="Company name" id="exp-org" /></div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">Start Date</label><input className="nc-add-form-input" placeholder="e.g. Jan 2020" id="exp-start" /></div>
                      <div className="nc-add-form-group"><label className="nc-add-form-label">End Date</label><input className="nc-add-form-input" placeholder="e.g. Dec 2023 or leave empty" id="exp-end" /></div>
                      <div className="nc-add-form-group full"><label className="nc-add-form-label">Description</label><textarea className="nc-add-form-textarea" placeholder="Job responsibilities..." id="exp-desc" /></div>
                      <div className="nc-add-form-actions">
                        <button className="nc-cancel-btn" onClick={() => setShowExpForm(false)}>Cancel</button>
                        <button className="nc-save-btn" onClick={() => {
                          const title = document.getElementById('exp-title').value;
                          const org = document.getElementById('exp-org').value;
                          const start = document.getElementById('exp-start').value;
                          const end = document.getElementById('exp-end').value;
                          const desc = document.getElementById('exp-desc').value;
                          if (title && org) { setExperience([...experience, { title, organization: org, startDate: start, endDate: end, description: desc }]); setShowExpForm(false); }
                        }}>Add</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SKILLS TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'skills' && (
        <section className="nc-section">
          <div className="nc-section-header">
            <h2 className="nc-section-title">Your Skills</h2>
            <button className="nc-upload-btn" onClick={() => fileInputRef.current?.click()}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
              Upload .md
            </button>
            <input ref={fileInputRef} type="file" accept=".md" onChange={handleUpload} style={{ display: 'none' }} />
          </div>
          <p className="nc-section-desc">Upload markdown files to teach Bianca custom skills and preferences.</p>
          {loading ? <div className="nc-loading">Loading skills...</div> : skills.length === 0 ? (
            <div className="nc-empty">
              <div className="nc-empty-icon"><svg width="32" height="32" viewBox="0 0 32 32" fill="none"><rect x="7" y="4" width="18" height="24" rx="2" stroke="currentColor" strokeWidth="1.5"/><path d="M12 12H20M12 16H18M12 20H16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg></div>
              <div className="nc-empty-text">No skills uploaded yet</div>
              <div className="nc-empty-hint">Upload a .md file to get started</div>
            </div>
          ) : (
            <div className="nc-skills-list">
              {skills.map((skill) => (
                <div key={skill.skill_id} className="nc-skill-card">
                  <div className="nc-skill-icon"><svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="3" y="2" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.2"/><path d="M6 6H12M6 9H11M6 12H9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg></div>
                  <div className="nc-skill-info">
                    <div className="nc-skill-title">{skill.title}</div>
                    <div className="nc-skill-meta">{skill.filename} &middot; {formatSize(skill.size_bytes)} &middot; {formatDate(skill.created_at)}</div>
                  </div>
                  <div className="nc-skill-actions">
                    {skill.source !== 'marketplace' && (
                      <button className="nc-skill-publish" onClick={() => handlePublish(skill.skill_id)} disabled={publishingId === skill.skill_id}>
                        {publishingId === skill.skill_id ? '...' : 'Publish'}
                      </button>
                    )}
                    <button className="nc-skill-delete" onClick={() => handleDeleteSkill(skill.skill_id, skill.filename)}><svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* WORLD MODEL TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'worldmodel' && (
        <section className="nc-section">
          <h2 className="nc-section-title">World Model</h2>
          <p className="nc-section-desc">Environmental and business context the AI uses for decision-making.</p>

          <div className="nc-worldmodel-categories">
            {WORLD_MODEL_CATEGORIES.map((c) => (
              <button key={c.id} className={`nc-worldmodel-cat${worldModelCat === c.id ? ' active' : ''}`} onClick={() => setWorldModelCat(c.id)}>{c.label}</button>
            ))}
          </div>

          {filteredWorldModel.length === 0 ? (
            <div className="nc-empty-state">
              <div className="nc-empty-state-text">No entries in {WORLD_MODEL_CATEGORIES.find((c) => c.id === worldModelCat)?.label}</div>
              <div className="nc-empty-state-hint">Add context about your business environment</div>
            </div>
          ) : (
            <div className="nc-worldmodel-entries">
              {filteredWorldModel.map((e, i) => {
                const globalIndex = worldModelEntries.indexOf(e);
                return (
                  <div key={e.id || i} className="nc-worldmodel-entry">
                    <div className="nc-worldmodel-entry-body">
                      <div className="nc-worldmodel-entry-title">{e.title}</div>
                      <div className="nc-worldmodel-entry-content">{e.content}</div>
                    </div>
                    <span className="nc-worldmodel-entry-type">{e.dataType}</span>
                    <button className={`nc-worldmodel-toggle${e.enabled ? ' enabled' : ''}`}
                      onClick={() => handleToggleWorldModelEntry(e, globalIndex)} />
                    <button className="nc-contact-delete" onClick={() => handleDeleteWorldModelEntry(e.id, globalIndex)}>
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          <button className="nc-add-entry-btn" onClick={() => setShowWMForm(!showWMForm)}>{showWMForm ? 'Cancel' : '+ Add Entry'}</button>
          {showWMForm && (
            <div className="nc-add-form">
              <div className="nc-add-form-title">Add World Model Entry</div>
              <div className="nc-add-form-grid">
                <div className="nc-add-form-group"><label className="nc-add-form-label">Title</label><input className="nc-add-form-input" placeholder="Entry title" id="wm-title" /></div>
                <div className="nc-add-form-group"><label className="nc-add-form-label">Data Type</label>
                  <select className="nc-add-form-select" id="wm-type"><option value="text">Text</option><option value="url">URL</option><option value="toggle">Toggle</option><option value="select">Select</option></select>
                </div>
                <div className="nc-add-form-group full"><label className="nc-add-form-label">Content</label><textarea className="nc-add-form-textarea" placeholder="Entry content..." id="wm-content" /></div>
                <div className="nc-add-form-actions">
                  <button className="nc-cancel-btn" onClick={() => setShowWMForm(false)}>Cancel</button>
                  <button className="nc-save-btn" onClick={() => {
                    const title = document.getElementById('wm-title').value;
                    const dataType = document.getElementById('wm-type').value;
                    const content = document.getElementById('wm-content').value;
                    if (title) {
                      handleAddWorldModelEntry({ category: worldModelCat, title, content, dataType, enabled: true });
                    }
                  }}>Add</button>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SYSTEM PROMPT TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'prompt' && (
        <section className="nc-section">
          <h2 className="nc-section-title">System Prompt & Model</h2>
          <p className="nc-section-desc">Configure the AI's brain — model selection, temperature, and prompt preview.</p>

          {settingsLoading || !settings ? <div className="nc-loading">Loading...</div> : (
            <>
              <div className="nc-subsection">
                <h3 className="nc-subsection-title">Model</h3>
                <div className="nc-model-groups">
                  {MODEL_GROUPS.map((group) => (
                    <div key={group.provider} className="nc-model-group">
                      <div className="nc-model-group-label" style={{ color: group.color }}>
                        {group.provider}
                      </div>
                      <div className="nc-model-options">
                        {group.models.map((m) => (
                          <button
                            key={m.id}
                            className={`nc-model-chip${settings.model === m.id ? ' active' : ''}`}
                            style={settings.model === m.id ? { borderColor: group.color, color: group.color } : {}}
                            onClick={() => updateSetting('model', m.id)}
                          >
                            <span className="nc-model-chip-name">{m.label}</span>
                            <span className="nc-model-chip-desc">{m.desc}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {!settings.model?.startsWith('claude') && (
                  <div className="nc-model-apikey">
                    <label className="nc-form-label">Google / Gemini API Key</label>
                    <input
                      className="nc-form-input nc-apikey-input"
                      type="password"
                      placeholder="AIza… (or set GOOGLE_API_KEY in .env)"
                      value={settings.google_api_key || ''}
                      onChange={(e) => updateSetting('google_api_key', e.target.value)}
                    />
                    <div className="nc-subsection-hint">AI Studio key — leave blank to use Vertex AI with Application Default Credentials</div>
                  </div>
                )}

                {settings.model?.startsWith('claude') && (
                  <div className="nc-model-apikey">
                    <label className="nc-form-label">Anthropic API Key</label>
                    <input
                      className="nc-form-input nc-apikey-input"
                      type="password"
                      placeholder="sk-ant-api03-… (or set ANTHROPIC_API_KEY in .env)"
                      value={settings.anthropic_api_key || ''}
                      onChange={(e) => updateSetting('anthropic_api_key', e.target.value)}
                    />
                    <div className="nc-subsection-hint">Only required if not set in backend/.env</div>
                  </div>
                )}
              </div>

              <div className="nc-subsection">
                <h3 className="nc-subsection-title">Temperature</h3>
                <div className="nc-slider-row">
                  <span className="nc-prompt-stat">Precise</span>
                  <input type="range" className="nc-slider" min="0" max="1" step="0.1" value={settings.temperature}
                    onChange={(e) => updateSetting('temperature', parseFloat(e.target.value))} />
                  <span className="nc-prompt-stat">Creative</span>
                  <span className="nc-slider-value">{settings.temperature}</span>
                </div>
              </div>

              <div className="nc-subsection">
                <h3 className="nc-subsection-title">Custom Prompt Prefix</h3>
                <textarea className="nc-custom-prompt" value={settings.custom_prompt || ''}
                  onChange={(e) => updateSetting('custom_prompt', e.target.value)}
                  placeholder="Add custom instructions prepended to every prompt..." />
                <div className="nc-subsection-hint">Prepended before the assembled system prompt.</div>
              </div>

              {settingsDirty && (
                <div className="nc-edit-actions">
                  <button className="nc-save-btn" onClick={saveSettingsHandler} disabled={settingsSaving}>{settingsSaving ? 'Saving...' : 'Save Changes'}</button>
                </div>
              )}

              <div className="nc-subsection" style={{ marginTop: 28 }}>
                <h3 className="nc-subsection-title">Assembled System Prompt</h3>
                {promptLoading ? <div className="nc-loading">Loading preview...</div> : promptPreview ? (
                  <>
                    <div className="nc-prompt-preview"><pre>{promptPreview.prompt}</pre></div>
                    <div className="nc-prompt-meta">
                      <span className="nc-prompt-stat">{promptPreview.length.toLocaleString()} characters</span>
                      <button className="nc-prompt-refresh" onClick={refreshPrompt}>
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 1011.5-2.5M13.5 2v3.5H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                        Refresh
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
            </>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* CONTACTS TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'contacts' && (
        <section className="nc-section">
          <h2 className="nc-section-title">Contacts</h2>
          <p className="nc-section-desc">People the AI knows and can personalize interactions with.</p>

          <div className="nc-contacts-search">
            <input className="nc-contacts-search-input" placeholder="Search contacts..." value={contactSearch}
              onChange={(e) => setContactSearch(e.target.value)} />
          </div>

          {filteredContacts.length === 0 ? (
            <div className="nc-empty-state">
              <div className="nc-empty-state-text">{contactSearch ? 'No contacts match your search' : 'No contacts added yet'}</div>
              <div className="nc-empty-state-hint">Add contacts to help the AI personalize interactions</div>
            </div>
          ) : (
            <div className="nc-contacts-grid">
              {filteredContacts.map((c, i) => (
                <div key={c.id || i} className="nc-contact-card">
                  <div className="nc-contact-name">{c.firstName} {c.lastName}</div>
                  <div className="nc-contact-title">{c.title}</div>
                  <div className="nc-contact-detail"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M2 4l6 4 6-4M2 4v8h12V4" stroke="currentColor" strokeWidth="1.2"/></svg>{c.email}</div>
                  <div className="nc-contact-detail"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 2h3l2 4-2 2c1 2 3 4 5 5l2-2 4 2v3c0 1-1 2-2 2C6 16 0 10 0 4c0-1 1-2 2-2" stroke="currentColor" strokeWidth="1.2"/></svg>{c.phone}</div>
                  <div className="nc-contact-actions">
                    <button className="nc-contact-delete" onClick={() => handleDeleteContact(c.id, i)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <button className="nc-add-entry-btn" onClick={() => setShowContactForm(!showContactForm)}>{showContactForm ? 'Cancel' : '+ Add Contact'}</button>
          {showContactForm && (
            <div className="nc-add-form">
              <div className="nc-add-form-title">Add Contact</div>
              <div className="nc-add-form-grid">
                <div className="nc-add-form-group"><label className="nc-add-form-label">First Name</label><input className="nc-add-form-input" id="ct-fn" /></div>
                <div className="nc-add-form-group"><label className="nc-add-form-label">Last Name</label><input className="nc-add-form-input" id="ct-ln" /></div>
                <div className="nc-add-form-group"><label className="nc-add-form-label">Email</label><input className="nc-add-form-input" id="ct-email" /></div>
                <div className="nc-add-form-group"><label className="nc-add-form-label">Phone</label><input className="nc-add-form-input" id="ct-phone" /></div>
                <div className="nc-add-form-group"><label className="nc-add-form-label">Title</label><input className="nc-add-form-input" id="ct-title" /></div>
                <div className="nc-add-form-group"><label className="nc-add-form-label">Preferred Language</label>
                  <select className="nc-add-form-select" id="ct-lang">{LANGUAGES.map((l) => <option key={l}>{l}</option>)}</select>
                </div>
                <div className="nc-add-form-actions">
                  <button className="nc-cancel-btn" onClick={() => setShowContactForm(false)}>Cancel</button>
                  <button className="nc-save-btn" onClick={() => {
                    const fn = document.getElementById('ct-fn').value;
                    const ln = document.getElementById('ct-ln').value;
                    if (fn) {
                      handleAddContact({
                        firstName: fn, lastName: ln,
                        email: document.getElementById('ct-email').value,
                        phone: document.getElementById('ct-phone').value,
                        title: document.getElementById('ct-title').value,
                        language: document.getElementById('ct-lang').value,
                      });
                    }
                  }}>Add</button>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* ACCESS CONTROL TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'access' && (
        <section className="nc-section">
          <h2 className="nc-section-title">Access Control</h2>
          <p className="nc-section-desc">Define what the AI is allowed and not allowed to do.</p>

          <div className="nc-access-section">
            <div className="nc-access-title">Authorizations</div>
            <div className="nc-access-list">
              {authorizations.map((a, i) => (
                <div key={i} className="nc-access-item">
                  <span className="nc-access-item-text">{a}</span>
                  <button className="nc-access-item-delete" onClick={() => handleDeleteAuthorization(i)}>
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
                  </button>
                </div>
              ))}
            </div>
            <div className="nc-access-add">
              <input className="nc-access-input" placeholder="e.g. Send emails, Schedule meetings" value={authInput}
                onChange={(e) => setAuthInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleAddAuthorization(); }} />
              <button className="nc-access-add-btn" onClick={handleAddAuthorization}>Add</button>
            </div>
          </div>

          <div className="nc-access-section">
            <div className="nc-access-title">Constraints</div>
            <div className="nc-access-list">
              {constraints.map((c, i) => (
                <div key={i} className="nc-access-item">
                  <span className="nc-access-item-text">{c}</span>
                  <button className="nc-access-item-delete" onClick={() => handleDeleteConstraint(i)}>
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
                  </button>
                </div>
              ))}
            </div>
            <div className="nc-access-add">
              <input className="nc-access-input" placeholder="e.g. Never share financial data externally" value={constraintInput}
                onChange={(e) => setConstraintInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleAddConstraint(); }} />
              <button className="nc-access-add-btn" onClick={handleAddConstraint}>Add</button>
            </div>
          </div>
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* VALUES TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'values' && (
        <section className="nc-section">
          <h2 className="nc-section-title">Core Values & Principles</h2>
          <p className="nc-section-desc">Priority-ordered rules that govern decision making.</p>

          {valuesLoading ? <div className="nc-loading">Loading...</div> : values === null ? null : (
            <div className="nc-values-list">
              {values.map((v) => {
                const isEditing = editingPriority === v.priority;
                return (
                  <div key={v.priority} className="nc-value-card">
                    <div className="nc-value-priority">{v.priority}</div>
                    <div className="nc-value-body">
                      {isEditing ? (
                        <div className="nc-value-edit-form">
                          <input className="nc-value-edit-title" value={valueDraft.title} onChange={(e) => setValueDraft((d) => ({ ...d, title: e.target.value }))} autoFocus />
                          <textarea className="nc-value-edit-rule" value={valueDraft.rule} onChange={(e) => setValueDraft((d) => ({ ...d, rule: e.target.value }))} />
                          <div className="nc-edit-actions">
                            <button className="nc-cancel-btn" onClick={cancelEditValue}>Cancel</button>
                            <button className="nc-save-btn" onClick={saveValue} disabled={valuesSaving || !valueDraft.title.trim()}>{valuesSaving ? 'Saving...' : 'Save'}</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="nc-value-title">{v.title}</div>
                          <div className="nc-value-rule">{v.rule}</div>
                        </>
                      )}
                    </div>
                    {!isEditing && (
                      <button className="nc-value-edit-btn" onClick={() => startEditValue(v)}>
                        <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M11.5 2.5L13.5 4.5L5 13H3V11L11.5 2.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/></svg>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* INTEGRATIONS TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'integrations' && (
        <section className="nc-section">
          <h2 className="nc-section-title">Integrations & Templates</h2>
          <p className="nc-section-desc">Configure channels, templates, and external connections.</p>

          {settingsLoading || !settings ? <div className="nc-loading">Loading...</div> : (
            <>
              {/* Voice Prompt */}
              <div className="nc-integration-card">
                <div className="nc-integration-header">
                  <div className="nc-integration-icon"><svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 2v14M5 5l4-3 4 3M5 13l4 3 4-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
                  <span className="nc-integration-title">Voice Prompt</span>
                </div>
                <div className="nc-integration-desc">Opening greeting for phone calls.</div>
                <input className="nc-template-input" placeholder="Opening greeting, e.g. Hello {caller}!" value={settings.voice_greeting || ''} onChange={(e) => updateSetting('voice_greeting', e.target.value)} />
                <div style={{ marginTop: 10 }}>
                  <label className="nc-form-label">Voice System Prompt</label>
                  <textarea className="nc-custom-prompt" placeholder="Voice-specific instructions (keep under 500 chars)" value={settings.voice_prompt || ''} onChange={(e) => updateSetting('voice_prompt', e.target.value)} style={{ minHeight: 100 }} />
                  <div className="nc-subsection-hint">{(settings.voice_prompt || '').length}/1000 chars {(settings.voice_prompt || '').length > 500 && '(warning: keep under 500 for best results)'}</div>
                </div>
              </div>

              {/* Phone Number — Twilio Voice */}
              <div className="nc-integration-card">
                <div className="nc-integration-header">
                  <div className="nc-integration-icon">
                    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                      <path d="M4.5 2C4.5 2 3 2 3 3.5c0 1.2.7 4.3 4.5 8.1C11.3 15.4 14.4 16 15.5 16c1.5 0 1.5-1.5 1.5-1.5v-2.2c0-.4-.3-.8-.7-.9l-2.3-.5c-.4-.1-.8.1-1 .4l-.7.9c-.2.3-.6.4-.9.2-1-.6-3.2-2.8-3.8-3.8-.2-.3-.1-.7.2-.9l.9-.7c.3-.2.5-.6.4-1L9.4 3.7c-.1-.4-.5-.7-.9-.7H4.5z" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <span className="nc-integration-title">Phone Number</span>
                  {phoneNumber && <span className="nc-status-badge configured">Registered</span>}
                </div>
                <div className="nc-integration-desc">
                  Register your phone number so Bianca recognizes you when you call. Bianca will answer with full access to your Gmail, Calendar, Drive, and all tools.
                </div>
                <div style={{ marginBottom: 10 }}>
                  <label className="nc-form-label">Your Phone Number (E.164 format)</label>
                  <input
                    className="nc-template-input"
                    placeholder="+14155552671"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                  />
                  <div className="nc-subsection-hint">
                    Include country code, e.g. +1 for US. This must match the number you call from.
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="nc-save-btn"
                    disabled={phoneSaving || !phoneNumber.trim()}
                    onClick={async () => {
                      setPhoneSaving(true);
                      try {
                        await savePhoneNumber(user.userId, phoneNumber.trim());
                        addToast('Phone number saved — Bianca will recognize your calls.', 'success');
                      } catch (err) {
                        addToast(`Failed to save: ${err.message}`, 'error');
                      } finally {
                        setPhoneSaving(false);
                      }
                    }}
                  >
                    {phoneSaving ? 'Saving...' : 'Save Number'}
                  </button>
                  {phoneNumber && (
                    <button
                      className="nc-save-btn"
                      style={{ background: 'rgba(224,90,90,0.12)', borderColor: 'rgba(224,90,90,0.3)', color: '#e05a5a' }}
                      disabled={phoneSaving}
                      onClick={async () => {
                        setPhoneSaving(true);
                        try {
                          await savePhoneNumber(user.userId, '');
                          setPhoneNumber('');
                          addToast('Phone number removed.', 'info');
                        } catch (err) {
                          addToast(`Failed to remove: ${err.message}`, 'error');
                        } finally {
                          setPhoneSaving(false);
                        }
                      }}
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>

              {/* Email Agent */}
              <div className="nc-integration-card">
                <div className="nc-integration-header">
                  <div className="nc-integration-icon">
                    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                      <path d="M2 4l7 5 7-5M2 4v10h14V4" stroke="currentColor" strokeWidth="1.3"/>
                    </svg>
                  </div>
                  <span className="nc-integration-title">Email Agent</span>
                  {emailAgentStatus?.watch_active && (
                    <span className="nc-status-badge configured">Active</span>
                  )}
                  {emailAgentStatus?.enabled && !emailAgentStatus?.watch_active && (
                    <span className="nc-status-badge" style={{ background: 'rgba(224,90,90,0.15)', color: '#e05a5a', borderColor: 'rgba(224,90,90,0.3)' }}>Watch Expired</span>
                  )}
                </div>
                <div className="nc-integration-desc">
                  Bianca monitors a Gmail label and auto-replies to incoming emails using your full persona and context. Powered by Gmail Push Notifications — instant, no polling.
                </div>

                {emailAgentLoading ? (
                  <div className="nc-loading" style={{ padding: '8px 0' }}>Loading...</div>
                ) : (
                  <>
                    <div style={{ marginBottom: 10 }}>
                      <label className="nc-form-label">Gmail Label to Watch</label>
                      <input
                        className="nc-template-input"
                        placeholder="e.g. Bianca_Contacts"
                        value={emailAgentLabelInput}
                        onChange={(e) => setEmailAgentLabelInput(e.target.value)}
                        disabled={emailAgentStatus?.enabled}
                      />
                      <div className="nc-subsection-hint">
                        Create this label in Gmail and set up a filter to route emails there. Bianca will only reply to emails in this label.
                      </div>
                    </div>

                    {emailAgentStatus?.enabled && (
                      <div style={{ marginBottom: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                        Watching <strong style={{ color: 'var(--text-secondary)' }}>{emailAgentStatus.label_name}</strong>
                        {emailAgentStatus.replied_count > 0 && (
                          <> · Replied to <strong style={{ color: 'var(--accent-gold)' }}>{emailAgentStatus.replied_count}</strong> email{emailAgentStatus.replied_count !== 1 ? 's' : ''}</>
                        )}
                        {emailAgentStatus.watch_expiry && (
                          <> · Watch renews automatically</>
                        )}
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: 8 }}>
                      {!emailAgentStatus?.enabled ? (
                        <button
                          className="nc-save-btn"
                          disabled={emailAgentSaving || !emailAgentLabelInput.trim()}
                          onClick={async () => {
                            setEmailAgentSaving(true);
                            try {
                              const result = await enableEmailAgent(user.userId, emailAgentLabelInput.trim());
                              setEmailAgentStatus({ enabled: true, label_name: result.label_name, watch_active: true, watch_expiry: result.watch_expiry, replied_count: 0 });
                              addToast(`Email agent enabled — watching "${result.label_name}"`, 'success');
                            } catch (err) {
                              addToast(`Failed to enable: ${err.message}`, 'error');
                            } finally {
                              setEmailAgentSaving(false);
                            }
                          }}
                        >
                          {emailAgentSaving ? 'Enabling...' : 'Enable Agent'}
                        </button>
                      ) : (
                        <button
                          className="nc-save-btn"
                          style={{ background: 'rgba(224,90,90,0.12)', borderColor: 'rgba(224,90,90,0.3)', color: '#e05a5a' }}
                          disabled={emailAgentSaving}
                          onClick={async () => {
                            setEmailAgentSaving(true);
                            try {
                              await disableEmailAgent(user.userId);
                              setEmailAgentStatus((prev) => ({ ...prev, enabled: false, watch_active: false }));
                              addToast('Email agent disabled', 'info');
                            } catch (err) {
                              addToast(`Failed to disable: ${err.message}`, 'error');
                            } finally {
                              setEmailAgentSaving(false);
                            }
                          }}
                        >
                          {emailAgentSaving ? 'Disabling...' : 'Disable Agent'}
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* GWS Templates */}
              <div className="nc-integration-card">
                <div className="nc-integration-header">
                  <div className="nc-integration-icon"><svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="3" width="14" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><rect x="5" y="6" width="8" height="6" rx="0.5" stroke="currentColor" strokeWidth="1" strokeDasharray="2 1"/></svg></div>
                  <span className="nc-integration-title">Google Slides Template</span>
                  {settings.slides_template_id && <span className="nc-status-badge configured">Configured</span>}
                </div>
                <div className="nc-integration-desc">Template for branded presentations.</div>
                <input className="nc-template-input" placeholder="Paste Slides URL or template ID" value={settings.slides_template_id || ''} onChange={(e) => updateSetting('slides_template_id', e.target.value)} />
              </div>

              <div className="nc-integration-card">
                <div className="nc-integration-header">
                  <div className="nc-integration-icon"><svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="3" y="2" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M6 6H12M6 9H11M6 12H9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg></div>
                  <span className="nc-integration-title">Google Docs Template</span>
                  {settings.docs_template_id && <span className="nc-status-badge configured">Configured</span>}
                </div>
                <div className="nc-integration-desc">Template for branded documents.</div>
                <input className="nc-template-input" placeholder="Paste Docs URL or template ID" value={settings.docs_template_id || ''} onChange={(e) => updateSetting('docs_template_id', e.target.value)} />
              </div>

              <div className="nc-integration-card">
                <div className="nc-integration-header">
                  <div className="nc-integration-icon"><svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="2" width="14" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M2 6h14M2 10h14M2 14h14M6 2v14M10 2v14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.5"/></svg></div>
                  <span className="nc-integration-title">Google Sheets Template</span>
                  {settings.sheets_template_id && <span className="nc-status-badge configured">Configured</span>}
                </div>
                <div className="nc-integration-desc">Template for branded spreadsheets.</div>
                <input className="nc-template-input" placeholder="Paste Sheets URL or template ID" value={settings.sheets_template_id || ''} onChange={(e) => updateSetting('sheets_template_id', e.target.value)} />
              </div>

              {settingsDirty && (
                <div className="nc-edit-actions">
                  <button className="nc-save-btn" onClick={saveSettingsHandler} disabled={settingsSaving}>{settingsSaving ? 'Saving...' : 'Save Changes'}</button>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TASKS TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'tasks' && (
        <section className="nc-section">
          <div className="nc-section-header">
            <h2 className="nc-section-title">Background Tasks</h2>
            {tasks.length > 0 && (
              <button className="nc-export-btn" onClick={handleExportTasks}>Export JSON</button>
            )}
          </div>
          <p className="nc-section-desc">Monitor long-running operations like document creation, emails, and presentations.</p>

          <div className="nc-tasks-filters">
            {['all', 'pending', 'running', 'completed', 'failed'].map((f) => (
              <button key={f} className={`nc-tasks-filter${tasksFilter === f ? ' active' : ''}`} onClick={() => setTasksFilter(f)}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
                {f !== 'all' && <span className="nc-tasks-filter-count">{tasks.filter((t) => t.status === f).length}</span>}
                {f === 'all' && <span className="nc-tasks-filter-count">{tasks.length}</span>}
              </button>
            ))}
          </div>

          {tasksLoading ? <div className="nc-loading">Loading tasks...</div> : filteredTasks.length === 0 ? (
            <div className="nc-empty-state">
              <div className="nc-empty-state-text">{tasksFilter === 'all' ? 'No tasks yet' : `No ${tasksFilter} tasks`}</div>
              <div className="nc-empty-state-hint">Tasks are created automatically when the AI performs long-running operations</div>
            </div>
          ) : (
            <div className="nc-tasks-list">
              {paginatedTasks.map((task) => (
                <div key={task.task_id} className={`nc-task-card nc-task-${task.status}`}>
                  <div className="nc-task-card-header">
                    <span className="nc-task-icon">{getTaskIcon(task.task_type)}</span>
                    <div className="nc-task-info">
                      <div className="nc-task-type">{task.task_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</div>
                      <div className="nc-task-time">{formatTimeAgo(task.created_at)}</div>
                    </div>
                    <span className="nc-task-status" style={{ color: getStatusColor(task.status) }}>
                      {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                    </span>
                  </div>

                  {task.status === 'running' && (
                    <div className="nc-task-progress">
                      <div className="nc-task-progress-bar">
                        <div className="nc-task-progress-fill" style={{ width: `${task.progress}%` }} />
                      </div>
                      <span className="nc-task-progress-text">{task.progress_message || `${task.progress}%`}</span>
                    </div>
                  )}

                  {task.status === 'completed' && task.result && (
                    <div className="nc-task-result">
                      {task.result.url && (
                        <a href={task.result.url} target="_blank" rel="noopener noreferrer" className="nc-task-result-link">
                          Open Result
                        </a>
                      )}
                      {task.result.doc_id && <span className="nc-task-result-id">ID: {task.result.doc_id}</span>}
                      {task.result.message_id && <span className="nc-task-result-id">Sent</span>}
                    </div>
                  )}

                  {task.status === 'failed' && task.error && (
                    <div className="nc-task-error">{task.error}</div>
                  )}

                  <div className="nc-task-actions">
                    {task.status === 'pending' && (
                      <button className="nc-task-cancel-btn" onClick={() => handleCancelTask(task.task_id)}>Cancel</button>
                    )}
                    {task.status === 'failed' && (
                      <button className="nc-task-retry-btn" onClick={() => handleRetryTask(task.task_id)}>Retry</button>
                    )}
                    {(task.status === 'completed' || task.status === 'failed') && (
                      <button className="nc-task-delete-btn" onClick={() => handleDeleteTask(task.task_id)}>Remove</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {totalTaskPages > 1 && (
            <div className="nc-tasks-pagination">
              <button
                className="nc-tasks-page-btn"
                onClick={() => setTasksPage((p) => Math.max(1, p - 1))}
                disabled={tasksPage === 1}
              >Prev</button>
              <span className="nc-tasks-page-info">{tasksPage} / {totalTaskPages}</span>
              <button
                className="nc-tasks-page-btn"
                onClick={() => setTasksPage((p) => Math.min(totalTaskPages, p + 1))}
                disabled={tasksPage === totalTaskPages}
              >Next</button>
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SECURITY TAB */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'security' && (
        <section className="nc-section">
          <h2 className="nc-section-title">Security</h2>
          <p className="nc-section-desc">API keys and secrets status. These are managed through environment variables.</p>

          <div className="nc-security-grid">
            {SECURITY_KEYS.map((s) => {
              const isConfigured = securityStatus ? !!securityStatus[s.key] : null;
              return (
                <div key={s.key} className="nc-security-item">
                  <span className="nc-security-label">{s.label}</span>
                  {isConfigured === null ? (
                    <span className="nc-status-badge">Checking...</span>
                  ) : isConfigured ? (
                    <span className="nc-status-badge configured">Configured</span>
                  ) : (
                    <span className="nc-status-badge not-configured">Not Configured</span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="nc-security-note">
            API keys are managed through environment variables on the server. Contact your administrator to update these settings.
          </div>
        </section>
      )}
      {/* Toast notifications */}
      {toasts.length > 0 && (
        <div className="nc-toast-container">
          {toasts.map((toast) => (
            <div key={toast.id} className={`nc-toast nc-toast-${toast.type}`}>
              <span className="nc-toast-icon">
                {toast.type === 'completed' ? (
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M2 7l3 3 6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : toast.type === 'failed' ? (
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M2 2l9 9M11 2l-9 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                  </svg>
                ) : (
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M6.5 5.5v4M6.5 3.5v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                  </svg>
                )}
              </span>
              {toast.message}
            </div>
          ))}
        </div>
      )}
      <Footer className="nc-footer" />
    </div>
  );
}
