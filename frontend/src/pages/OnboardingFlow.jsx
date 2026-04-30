import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../hooks/useAuth';
import { completeOnboarding, updateOnboardingStep, chatOnboarding } from '../api/client';
import './OnboardingFlow.css';

const STEPS = [
  { id: 1, label: 'Identity',  icon: '✦' },
  { id: 2, label: 'API Key',   icon: '⬡' },
  { id: 3, label: 'Persona',   icon: '◈' },
  { id: 4, label: 'Values',    icon: '◇' },
];

const MODEL_OPTIONS = [
  { id: 'claude-sonnet-4-6',  label: 'Claude Sonnet 4.6',  provider: 'Anthropic', desc: 'Best balance of speed and intelligence' },
  { id: 'claude-opus-4-7',    label: 'Claude Opus 4.7',    provider: 'Anthropic', desc: 'Latest Opus — most powerful' },
  { id: 'claude-opus-4-6',    label: 'Claude Opus 4.6',    provider: 'Anthropic', desc: 'Most powerful — deepest reasoning' },
  { id: 'gemini-2.5-flash',   label: 'Gemini 2.5 Flash',   provider: 'Google',    desc: 'Fast and cost-efficient' },
  { id: 'gemini-2.5-pro',     label: 'Gemini 2.5 Pro',     provider: 'Google',    desc: 'Most capable Gemini model' },
];

const LANGUAGES = ['English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
  'Dutch', 'Japanese', 'Korean', 'Chinese', 'Arabic', 'Hindi'];

const DEFAULT_VALUES = [
  { priority: 1, title: 'Draft Before Send', rule: 'Never send an email without explicit confirmation. Always draft first.' },
  { priority: 2, title: 'Confirm Before Irreversible Actions', rule: 'Always confirm before taking actions that cannot be undone.' },
  { priority: 3, title: 'Time Is the Scarcest Resource', rule: 'Be concise. Do not repeat yourself. Move fast, act with confidence.' },
  { priority: 4, title: 'One Clarifying Question at a Time', rule: 'If something is ambiguous, ask one sharp question — not several.' },
  { priority: 5, title: 'Close the Loop', rule: 'After completing any action, confirm what was done in one clear sentence.' },
];

// ── Mode Selector ─────────────────────────────────────────────────────────────

function ModeSelector({ onSelect }) {
  return (
    <div className="ob-mode-selector">
      <h2 className="ob-step-title">How would you like to set up your agent?</h2>
      <p className="ob-step-desc">Choose the method that works best for you. Both take about 2 minutes.</p>

      <div className="ob-mode-cards">
        <button type="button" className="ob-mode-card" onClick={() => onSelect('manual')}>
          <div className="ob-mode-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="3"/>
              <path d="M7 8h10M7 12h10M7 16h6"/>
            </svg>
          </div>
          <div className="ob-mode-body">
            <div className="ob-mode-title">Manual setup</div>
            <div className="ob-mode-desc">Fill in a structured 4-step form at your own pace.</div>
          </div>
          <div className="ob-mode-arrow">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </button>

        <button type="button" className="ob-mode-card ob-mode-card--ai" onClick={() => onSelect('ai')}>
          <div className="ob-mode-icon ob-mode-icon--ai">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
              <path d="M8 10h.01M12 10h.01M16 10h.01"/>
            </svg>
          </div>
          <div className="ob-mode-body">
            <div className="ob-mode-title">
              Set up with AI
              <span className="ob-mode-badge">Recommended</span>
            </div>
            <div className="ob-mode-desc">Chat with an AI that asks the right questions for you.</div>
          </div>
          <div className="ob-mode-arrow">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </button>
      </div>
    </div>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="ob-chat-bubble ob-chat-bubble--agent">
      <div className="ob-typing">
        <span /><span /><span />
      </div>
    </div>
  );
}

// ── Key Entry (before chat starts) ───────────────────────────────────────────

function KeyEntry({ onStart, onBack }) {
  const [keyInput, setKeyInput] = useState('');
  const [showKey, setShowKey]   = useState(false);
  const [error, setError]       = useState('');

  const detected = keyInput.trim().startsWith('sk-') ? 'anthropic' : keyInput.trim().startsWith('AIza') ? 'google' : null;

  const handleStart = () => {
    if (!keyInput.trim()) { setError('Please enter an API key to continue.'); return; }
    if (!detected) { setError('Key not recognised. Gemini keys start with AIza… and Anthropic keys start with sk-ant-…'); return; }
    onStart(keyInput.trim(), detected);
  };

  return (
    <div className="ob-key-entry">
      <h2 className="ob-step-title">Connect your API key</h2>
      <p className="ob-step-desc">
        The AI guide runs on your own key — no server key needed.
        Paste a <strong>Google AI Studio</strong> key or an <strong>Anthropic</strong> key below.
      </p>

      <div className="ob-key-entry-options">
        <a className="ob-key-entry-link" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
          Get a Gemini key → aistudio.google.com
        </a>
        <a className="ob-key-entry-link" href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          Get an Anthropic key → console.anthropic.com
        </a>
      </div>

      <div className="ob-field" style={{ marginTop: 20 }}>
        <label className="ob-label">Your API Key</label>
        <div className="ob-key-row">
          <input
            className={`ob-input ob-input--mono ${detected ? 'ob-input--detected' : ''}`}
            type={showKey ? 'text' : 'password'}
            value={keyInput}
            onChange={(e) => { setKeyInput(e.target.value); setError(''); }}
            onKeyDown={(e) => { if (e.key === 'Enter') handleStart(); }}
            placeholder="AIzaSy… or sk-ant-api03-…"
            autoFocus
          />
          <button type="button" className="ob-eye-btn" onClick={() => setShowKey((v) => !v)}>
            {showKey ? '🙈' : '👁'}
          </button>
        </div>
        {detected && (
          <div className="ob-key-detected">
            {detected === 'google' ? '✓ Gemini key detected — will use Gemini 2.5 Flash' : '✓ Anthropic key detected — will use Claude Haiku'}
          </div>
        )}
        {error && <div className="ob-error" style={{ marginTop: 8 }}>{error}</div>}
      </div>

      <div className="ob-byok-note">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.2"/><path d="M8 7v4M8 5v1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        Your key is sent directly from your browser to our backend and used only for this setup session. It will be saved encrypted in your private Firestore profile.
      </div>

      <div className="ob-nav" style={{ marginTop: 24 }}>
        <button type="button" className="ob-btn ob-btn--ghost" onClick={onBack}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M10 4l-4 4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Back
        </button>
        <div className="ob-nav-spacer" />
        <button type="button" className="ob-btn ob-btn--primary" onClick={handleStart} disabled={!keyInput.trim()}>
          Start chat
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
      </div>
    </div>
  );
}

// ── AI Chat Onboarding ────────────────────────────────────────────────────────

function AIChatOnboarding({ user, onComplete, onBack }) {
  // phase: 'key' = key entry, 'chat' = conversation
  const [phase, setPhase]         = useState('key');
  const [apiKey, setApiKey]       = useState('');
  const [provider, setProvider]   = useState('');

  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError]         = useState('');
  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const initialized = useRef(false);

  const handleKeySubmit = (key, prov) => {
    setApiKey(key);
    setProvider(prov);
    setPhase('chat');
  };

  // Kick off the first greeting once chat phase starts
  useEffect(() => {
    if (phase !== 'chat' || initialized.current) return;
    initialized.current = true;
    sendMessage('', [], apiKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const sendMessage = async (userText, currentHistory, key) => {
    setError('');
    setLoading(true);
    try {
      const res = await chatOnboarding(user.userId, userText || '__START__', currentHistory, key || apiKey);
      const newMessages = userText
        ? [...currentHistory, { role: 'user', text: userText }, { role: 'model', text: res.reply }]
        : [{ role: 'model', text: res.reply }];

      setMessages(newMessages);

      if (res.is_complete) {
        setFinishing(true);
        const fields = res.extracted || {};
        // Inject the BYOK key into the right field based on provider
        const isGoogle = (res.provider || provider) === 'google';
        await completeOnboarding(user.userId, {
          ai_name:           fields.ai_name          || 'Bianc.ai',
          ai_role:           fields.ai_role           || 'AI Chief of Staff',
          primary_language:  fields.primary_language  || 'English',
          model:             fields.model             || (isGoogle ? 'gemini-2.5-flash' : 'claude-sonnet-4-6'),
          anthropic_api_key: isGoogle ? '' : apiKey,
          google_api_key:    isGoogle ? apiKey : '',
          persona:           fields.persona           || '',
          expertise:         fields.expertise         || '',
          company:           fields.company           || '',
          values:            Array.isArray(fields.values) && fields.values.length ? fields.values : DEFAULT_VALUES,
        });
        onComplete();
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading || finishing) return;
    setInput('');
    sendMessage(text, messages, apiKey);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Key entry phase
  if (phase === 'key') {
    return <KeyEntry onStart={handleKeySubmit} onBack={onBack} />;
  }

  // Finishing
  if (finishing) {
    return (
      <div className="ob-chat-finishing">
        <div className="ob-spinner ob-spinner--lg" />
        <p>Launching your agent…</p>
      </div>
    );
  }

  // Chat phase
  return (
    <div className="ob-chat-root">
      <div className="ob-chat-header">
        <div className="ob-chat-avatar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4l3 3"/>
          </svg>
        </div>
        <div className="ob-chat-header-text">
          <span className="ob-chat-name">Bianc.ai Setup</span>
          <span className="ob-chat-status">
            {provider === 'anthropic' ? 'Powered by Claude Haiku' : 'Powered by Gemini 2.5 Flash'}
          </span>
        </div>
        <button type="button" className="ob-chat-back-btn" onClick={() => { setPhase('key'); initialized.current = false; setMessages([]); }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M10 4l-4 4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Change key
        </button>
      </div>

      <div className="ob-chat-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`ob-chat-bubble ${msg.role === 'user' ? 'ob-chat-bubble--user' : 'ob-chat-bubble--agent'}`}
          >
            {msg.role === 'user' ? msg.text : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
            )}
          </div>
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {error && <div className="ob-error ob-error--chat">{error}</div>}

      <div className="ob-chat-input-row">
        <textarea
          ref={inputRef}
          className="ob-chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Type your reply…"
          rows={1}
          disabled={loading || finishing}
        />
        <button
          type="button"
          className="ob-chat-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || loading || finishing}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Main OnboardingFlow ───────────────────────────────────────────────────────

export function OnboardingFlow() {
  const { user, markOnboardingComplete } = useAuth();

  // null = mode selector, 'manual' = form, 'ai' = chat
  const [mode, setMode] = useState(null);

  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Step 1 — Identity
  const [agentName, setAgentName]   = useState('Bianc.ai');
  const [agentRole, setAgentRole]   = useState('AI Chief of Staff');
  const [language, setLanguage]     = useState('English');
  const [model, setModel]           = useState('claude-sonnet-4-6');

  // Step 2 — API Keys
  const [anthropicKey, setAnthropicKey] = useState('');
  const [googleKey, setGoogleKey]       = useState('');
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [showGoogleKey, setShowGoogleKey]       = useState(false);

  // Step 3 — Persona
  const [persona, setPersona]     = useState('');
  const [expertise, setExpertise] = useState('');
  const [company, setCompany]     = useState('');

  // Step 4 — Values
  const [values, setValues] = useState(DEFAULT_VALUES);

  const selectedModel   = MODEL_OPTIONS.find((m) => m.id === model);
  const isAnthropicModel = model.startsWith('claude');

  const goNext = async () => {
    setError('');
    if (step === 1) {
      if (!agentName.trim()) { setError('Agent name is required.'); return; }
      await updateOnboardingStep(user.userId, 2).catch(() => {});
      setStep(2);
    } else if (step === 2) {
      if (isAnthropicModel && !anthropicKey.trim()) {
        setError('An Anthropic API key is required for Claude models.');
        return;
      }
      if (!isAnthropicModel && !googleKey.trim()) {
        setError('A Google API key is required for Gemini models.');
        return;
      }
      await updateOnboardingStep(user.userId, 3).catch(() => {});
      setStep(3);
    } else if (step === 3) {
      if (!persona.trim()) { setError('Write at least a short persona description.'); return; }
      await updateOnboardingStep(user.userId, 4).catch(() => {});
      setStep(4);
    }
  };

  const goBack = () => { setError(''); setStep((s) => s - 1); };

  const handleComplete = async () => {
    setError('');
    setSaving(true);
    try {
      await completeOnboarding(user.userId, {
        ai_name: agentName.trim(),
        ai_role: agentRole.trim() || 'AI Chief of Staff',
        primary_language: language,
        model,
        anthropic_api_key: anthropicKey.trim(),
        google_api_key: googleKey.trim(),
        persona: persona.trim(),
        expertise: expertise.trim(),
        company: company.trim(),
        values,
      });
      markOnboardingComplete();
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const updateValue = (priority, field, val) => {
    setValues((prev) => prev.map((v) => v.priority === priority ? { ...v, [field]: val } : v));
  };

  return (
    <div className="ob-root">
      <div className="ob-bg-glow" />

      <div className={`ob-card ${mode === 'ai' ? 'ob-card--chat' : ''}`}>
        {/* Header */}
        <div className="ob-header">
          <div className="ob-logo-row">
            <img
              src={`${import.meta.env.BASE_URL}lyftbridge-wordmark-dark.png`}
              alt="Lyftbridge"
              className="ob-logo-wordmark"
            />
          </div>
          <h1 className="ob-headline">Set up your AI agent</h1>
          <p className="ob-sub">Configure your agent in minutes. You can change everything later in Neural Config.</p>
        </div>

        {/* Mode selector */}
        {mode === null && <ModeSelector onSelect={setMode} />}

        {/* AI chat mode */}
        {mode === 'ai' && (
          <AIChatOnboarding
            user={user}
            onComplete={markOnboardingComplete}
            onBack={() => setMode(null)}
          />
        )}

        {/* Manual form mode */}
        {mode === 'manual' && (
          <>
            {/* Step progress */}
            <div className="ob-steps">
              {STEPS.map((s, i) => (
                <div key={s.id} className={`ob-step ${step === s.id ? 'ob-step--active' : ''} ${step > s.id ? 'ob-step--done' : ''}`}>
                  <div className="ob-step-bubble">
                    {step > s.id ? (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    ) : (
                      <span>{s.icon}</span>
                    )}
                  </div>
                  <span className="ob-step-label">{s.label}</span>
                  {i < STEPS.length - 1 && <div className="ob-step-line" />}
                </div>
              ))}
            </div>

            {/* Step content */}
            <div className="ob-content">

              {/* ── Step 1: Identity ── */}
              {step === 1 && (
                <div className="ob-step-body">
                  <h2 className="ob-step-title">Name your agent</h2>
                  <p className="ob-step-desc">Give your AI a name, role, and preferred language.</p>

                  <div className="ob-field">
                    <label className="ob-label">Agent Name</label>
                    <input
                      className="ob-input"
                      value={agentName}
                      onChange={(e) => setAgentName(e.target.value)}
                      placeholder="e.g. Bianc.ai, Aria, Max…"
                      maxLength={40}
                    />
                  </div>

                  <div className="ob-field">
                    <label className="ob-label">Role / Title</label>
                    <input
                      className="ob-input"
                      value={agentRole}
                      onChange={(e) => setAgentRole(e.target.value)}
                      placeholder="e.g. AI Chief of Staff, Executive Assistant…"
                      maxLength={60}
                    />
                  </div>

                  <div className="ob-field">
                    <label className="ob-label">Primary Language</label>
                    <select className="ob-select" value={language} onChange={(e) => setLanguage(e.target.value)}>
                      {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>

                  <div className="ob-field">
                    <label className="ob-label">AI Model</label>
                    <div className="ob-model-grid">
                      {MODEL_OPTIONS.map((m) => (
                        <button
                          key={m.id}
                          type="button"
                          className={`ob-model-card ${model === m.id ? 'ob-model-card--selected' : ''}`}
                          onClick={() => setModel(m.id)}
                        >
                          <div className="ob-model-provider">{m.provider}</div>
                          <div className="ob-model-name">{m.label}</div>
                          <div className="ob-model-desc">{m.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ── Step 2: API Key ── */}
              {step === 2 && (
                <div className="ob-step-body">
                  <h2 className="ob-step-title">Connect your API key</h2>
                  <p className="ob-step-desc">
                    You selected <strong>{selectedModel?.label}</strong> ({selectedModel?.provider}).
                    {isAnthropicModel
                      ? ' Enter your Anthropic API key below.'
                      : ' Enter your Google AI Studio API key below.'}
                  </p>

                  {isAnthropicModel ? (
                    <div className="ob-field">
                      <label className="ob-label">Anthropic API Key</label>
                      <div className="ob-key-row">
                        <input
                          className="ob-input ob-input--mono"
                          type={showAnthropicKey ? 'text' : 'password'}
                          value={anthropicKey}
                          onChange={(e) => setAnthropicKey(e.target.value)}
                          placeholder="sk-ant-api03-…"
                        />
                        <button type="button" className="ob-eye-btn" onClick={() => setShowAnthropicKey((v) => !v)}>
                          {showAnthropicKey ? '🙈' : '👁'}
                        </button>
                      </div>
                      <a className="ob-key-link" href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer">
                        Get your key → console.anthropic.com
                      </a>
                    </div>
                  ) : (
                    <div className="ob-field">
                      <label className="ob-label">Google AI Studio API Key</label>
                      <div className="ob-key-row">
                        <input
                          className="ob-input ob-input--mono"
                          type={showGoogleKey ? 'text' : 'password'}
                          value={googleKey}
                          onChange={(e) => setGoogleKey(e.target.value)}
                          placeholder="AIzaSy…"
                        />
                        <button type="button" className="ob-eye-btn" onClick={() => setShowGoogleKey((v) => !v)}>
                          {showGoogleKey ? '🙈' : '👁'}
                        </button>
                      </div>
                      <a className="ob-key-link" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
                        Get your key → aistudio.google.com
                      </a>
                    </div>
                  )}

                  <div className="ob-byok-note">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.2"/><path d="M8 7v4M8 5v1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
                    Your key is stored encrypted in your private Firestore database. It is never shared with other users or logged.
                  </div>
                </div>
              )}

              {/* ── Step 3: Persona ── */}
              {step === 3 && (
                <div className="ob-step-body">
                  <h2 className="ob-step-title">Define {agentName || 'your agent'}'s character</h2>
                  <p className="ob-step-desc">Describe who your agent is and what they're expert in. The more specific, the better.</p>

                  <div className="ob-field">
                    <label className="ob-label">
                      Persona & Identity <span className="ob-required">*</span>
                    </label>
                    <textarea
                      className="ob-textarea"
                      value={persona}
                      onChange={(e) => setPersona(e.target.value)}
                      placeholder={`${agentName || 'Bianc.ai'} is a sharp, direct advisor with a background in…\n\nSpeak with confidence and warmth. Prioritise clarity over formality.`}
                      rows={4}
                    />
                  </div>

                  <div className="ob-field">
                    <label className="ob-label">Domain Expertise</label>
                    <textarea
                      className="ob-textarea"
                      value={expertise}
                      onChange={(e) => setExpertise(e.target.value)}
                      placeholder="Areas of deep knowledge: e.g. SaaS go-to-market, financial modeling, engineering leadership…"
                      rows={3}
                    />
                  </div>

                  <div className="ob-field">
                    <label className="ob-label">Company / Product Context <span className="ob-optional">(optional)</span></label>
                    <textarea
                      className="ob-textarea"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="What company or product is this agent supporting? What's the mission?"
                      rows={3}
                    />
                  </div>
                </div>
              )}

              {/* ── Step 4: Values ── */}
              {step === 4 && (
                <div className="ob-step-body">
                  <h2 className="ob-step-title">Behavioral values</h2>
                  <p className="ob-step-desc">
                    These rules govern every action {agentName || 'your agent'} takes. Edit them to match how you want to work.
                  </p>

                  <div className="ob-values-list">
                    {values.map((v) => (
                      <div key={v.priority} className="ob-value-item">
                        <div className="ob-value-num">{v.priority}</div>
                        <div className="ob-value-fields">
                          <input
                            className="ob-input ob-input--value-title"
                            value={v.title}
                            onChange={(e) => updateValue(v.priority, 'title', e.target.value)}
                            placeholder="Value title"
                          />
                          <textarea
                            className="ob-textarea ob-textarea--value-rule"
                            value={v.rule}
                            onChange={(e) => updateValue(v.priority, 'rule', e.target.value)}
                            rows={2}
                            placeholder="What does this mean in practice?"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>

            {/* Error */}
            {error && <div className="ob-error">{error}</div>}

            {/* Navigation */}
            <div className="ob-nav">
              {step === 1 ? (
                <button type="button" className="ob-btn ob-btn--ghost" onClick={() => setMode(null)}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path d="M10 4l-4 4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Back
                </button>
              ) : (
                <button type="button" className="ob-btn ob-btn--ghost" onClick={goBack} disabled={saving}>
                  Back
                </button>
              )}
              <div className="ob-nav-spacer" />
              {step < 4 ? (
                <button type="button" className="ob-btn ob-btn--primary" onClick={goNext}>
                  Continue
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </button>
              ) : (
                <button type="button" className="ob-btn ob-btn--primary" onClick={handleComplete} disabled={saving}>
                  {saving ? (
                    <><span className="ob-spinner" /> Launching…</>
                  ) : (
                    <>Launch {agentName || 'Bianc.ai'} <span className="ob-launch-icon">⚡</span></>
                  )}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
