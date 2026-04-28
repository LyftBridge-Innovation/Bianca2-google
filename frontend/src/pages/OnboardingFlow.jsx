import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { completeOnboarding, updateOnboardingStep } from '../api/client';
import './OnboardingFlow.css';

const STEPS = [
  { id: 1, label: 'Identity',  icon: '✦' },
  { id: 2, label: 'API Key',   icon: '⬡' },
  { id: 3, label: 'Persona',   icon: '◈' },
  { id: 4, label: 'Values',    icon: '◇' },
];

const MODEL_OPTIONS = [
  { id: 'claude-sonnet-4-6',  label: 'Claude Sonnet 4.6',  provider: 'Anthropic', desc: 'Best balance of speed and intelligence' },
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

export function OnboardingFlow() {
  const { user, markOnboardingComplete } = useAuth();

  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Step 1 — Identity
  const [agentName, setAgentName]   = useState('Bianca');
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

  const selectedModel = MODEL_OPTIONS.find((m) => m.id === model);
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
      {/* Background ambient glow */}
      <div className="ob-bg-glow" />

      <div className="ob-card">
        {/* Header */}
        <div className="ob-header">
          <div className="ob-logo-row">
            <span className="ob-logo-mark">◈</span>
            <span className="ob-logo-name">Bianca</span>
          </div>
          <h1 className="ob-headline">Set up your AI agent</h1>
          <p className="ob-sub">Configure your agent in 4 steps. You can change everything later in Neural Config.</p>
        </div>

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
                  placeholder="e.g. Bianca, Aria, Max…"
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
                  placeholder={`${agentName || 'Bianca'} is a sharp, direct advisor with a background in…\n\nSpeak with confidence and warmth. Prioritise clarity over formality.`}
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
          {step > 1 && (
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
                <>Launch {agentName || 'Bianca'} <span className="ob-launch-icon">⚡</span></>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
