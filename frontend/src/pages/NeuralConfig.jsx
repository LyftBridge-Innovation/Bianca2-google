import { useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useSkills } from '../hooks/useSkills';
import './NeuralConfig.css';

export function NeuralConfig({ onGoToChat }) {
  const { user, logout } = useAuth();
  const { skills, loading, upload, deleteSkill } = useSkills(user.userId);
  const fileInputRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      await upload(file);
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    }
    // Reset input so the same file can be re-uploaded
    e.target.value = '';
  };

  const handleDelete = async (skillId, filename) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await deleteSkill(skillId);
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const formatDate = (isoString) => {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <div className="neural-config">
      {/* Header */}
      <div className="nc-header">
        <h1 className="nc-title">Neural Config</h1>
        <button className="nc-back-btn" onClick={onGoToChat}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M11 4L6 9L11 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Back to Chat
        </button>
      </div>

      {/* Profile Section */}
      <section className="nc-section">
        <h2 className="nc-section-title">Profile</h2>
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

      {/* Skills Section */}
      <section className="nc-section">
        <div className="nc-section-header">
          <h2 className="nc-section-title">Skills</h2>
          <button className="nc-upload-btn" onClick={() => fileInputRef.current?.click()}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Upload .md
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md"
            onChange={handleUpload}
            style={{ display: 'none' }}
          />
        </div>

        <p className="nc-section-desc">
          Upload markdown files to teach Bianca custom skills and preferences.
          Skills are matched to your messages and applied only when relevant.
        </p>

        {loading ? (
          <div className="nc-loading">Loading skills...</div>
        ) : skills.length === 0 ? (
          <div className="nc-empty">
            <div className="nc-empty-icon">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect x="7" y="4" width="18" height="24" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M12 12H20M12 16H18M12 20H16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="nc-empty-text">No skills uploaded yet</div>
            <div className="nc-empty-hint">Drop a .md file to get started</div>
          </div>
        ) : (
          <div className="nc-skills-list">
            {skills.map((skill) => (
              <div key={skill.skill_id} className="nc-skill-card">
                <div className="nc-skill-icon">
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <rect x="3" y="2" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
                    <path d="M6 6H12M6 9H11M6 12H9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                  </svg>
                </div>
                <div className="nc-skill-info">
                  <div className="nc-skill-title">{skill.title}</div>
                  <div className="nc-skill-meta">
                    {skill.filename} &middot; {formatSize(skill.size_bytes)} &middot; {formatDate(skill.created_at)}
                  </div>
                </div>
                <button
                  className="nc-skill-delete"
                  onClick={() => handleDelete(skill.skill_id, skill.filename)}
                  title="Delete skill"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
