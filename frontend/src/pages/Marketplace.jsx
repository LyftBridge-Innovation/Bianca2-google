import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../hooks/useAuth';
import { getMarketplaceSkills, installFromMarketplace, unpublishSkill } from '../api/client';
import { useSkills } from '../hooks/useSkills';
import './Marketplace.css';

export function Marketplace({ onGoToChat }) {
  const { user } = useAuth();
  const { skills: userSkills, refreshSkills } = useSkills(user.userId);

  // State
  const [skills, setSkills] = useState([]);
  const [filteredSkills, setFilteredSkills] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [loading, setLoading] = useState(true);
  const [installingId, setInstallingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [installedTitles, setInstalledTitles] = useState(new Set());

  // Load marketplace skills on mount
  useEffect(() => {
    loadMarketplaceSkills();
  }, []);

  // Update installed titles when user skills change
  useEffect(() => {
    setInstalledTitles(new Set(userSkills.map((s) => s.title.toLowerCase())));
  }, [userSkills]);

  // Filter skills when search changes
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredSkills(skills);
    } else {
      const q = searchQuery.toLowerCase();
      setFilteredSkills(
        skills.filter(
          (s) =>
            s.title?.toLowerCase().includes(q) ||
            s.description?.toLowerCase().includes(q) ||
            s.author_name?.toLowerCase().includes(q)
        )
      );
    }
  }, [searchQuery, skills]);

  const loadMarketplaceSkills = async () => {
    setLoading(true);
    try {
      const data = await getMarketplaceSkills();
      setSkills(data.skills || []);
      setFilteredSkills(data.skills || []);
    } catch (err) {
      console.error('Failed to load marketplace:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (skillId) => {
    setInstallingId(skillId);
    try {
      await installFromMarketplace(user.userId, skillId);
      await refreshSkills();
      await loadMarketplaceSkills(); // Refresh to show updated install count
    } catch (err) {
      alert(`Install failed: ${err.message}`);
    } finally {
      setInstallingId(null);
    }
  };

  const handleDelete = async (skillId) => {
    if (!confirm('Remove this skill from the marketplace? This cannot be undone.')) return;
    setDeletingId(skillId);
    try {
      await unpublishSkill(user.userId, skillId);
      setSelectedSkill(null);
      await loadMarketplaceSkills();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="marketplace">
      <header className="mp-header">
        <button onClick={onGoToChat} className="mp-back-btn">
          ← Back to Chat
        </button>
        <h1 className="mp-title">Skill Marketplace</h1>
        <p className="mp-subtitle">Discover and install skills from the community</p>
      </header>

      {/* Search Bar */}
      <div className="mp-search">
        <svg className="mp-search-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" />
          <path d="M12 12L17 17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          className="mp-search-input"
          placeholder="Search skills by name, description, or author..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button className="mp-search-clear" onClick={() => setSearchQuery('')}>
            ×
          </button>
        )}
      </div>

      {/* Skills Grid */}
      {loading ? (
        <div className="mp-loading">Loading marketplace...</div>
      ) : filteredSkills.length === 0 ? (
        <div className="mp-empty">
          <p>
            {searchQuery
              ? 'No skills match your search'
              : 'No skills in marketplace yet'}
          </p>
          {!searchQuery && <p className="mp-empty-hint">Be the first to publish!</p>}
        </div>
      ) : (
        <div className="mp-grid">
          {filteredSkills.map((skill) => {
            const isInstalled = installedTitles.has(skill.title?.toLowerCase());
            const isInstalling = installingId === skill.skill_id;

            return (
              <div key={skill.skill_id} className="mp-card">
                <div
                  className="mp-card-body"
                  onClick={() => setSelectedSkill(skill)}
                >
                  <h3 className="mp-card-title">{skill.title}</h3>
                  {skill.description && (
                    <p className="mp-card-desc">{skill.description}</p>
                  )}
                  <div className="mp-card-meta">
                    <span className="mp-author">by {skill.author_name}</span>
                    <span className="mp-installs">
                      {skill.install_count || 0} installs
                    </span>
                  </div>
                </div>
                <div className="mp-card-actions">
                  <button
                    className={`mp-install-btn ${isInstalled ? 'installed' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleInstall(skill.skill_id);
                    }}
                    disabled={isInstalled || isInstalling}
                  >
                    {isInstalling ? '...' : isInstalled ? 'Installed' : 'Install'}
                  </button>
                  {skill.author_user_id === user.userId && (
                    <button
                      className="mp-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(skill.skill_id);
                      }}
                      disabled={deletingId === skill.skill_id}
                      title="Remove from marketplace"
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Skill Detail Modal */}
      {selectedSkill && (
        <div
          className="mp-modal-overlay"
          onClick={() => setSelectedSkill(null)}
        >
          <div className="mp-modal" onClick={(e) => e.stopPropagation()}>
            <div className="mp-modal-header">
              <h2>{selectedSkill.title}</h2>
              <button
                className="mp-modal-close"
                onClick={() => setSelectedSkill(null)}
                title="Close"
              >
                ×
              </button>
            </div>
            <div className="mp-modal-meta">
              <span>by {selectedSkill.author_name}</span>
              <span>{selectedSkill.install_count || 0} installs</span>
            </div>
            <div className="mp-modal-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {selectedSkill.content}
              </ReactMarkdown>
            </div>
            <div className="mp-modal-footer">
              {selectedSkill.author_user_id === user.userId && (
                <button
                  className="mp-modal-delete"
                  onClick={() => handleDelete(selectedSkill.skill_id)}
                  disabled={deletingId === selectedSkill.skill_id}
                >
                  {deletingId === selectedSkill.skill_id ? '...' : 'Remove from Marketplace'}
                </button>
              )}
              <button
                className={`mp-modal-install ${installedTitles.has(selectedSkill.title?.toLowerCase()) ? 'installed' : ''}`}
                onClick={() => handleInstall(selectedSkill.skill_id)}
                disabled={
                  installedTitles.has(selectedSkill.title?.toLowerCase()) ||
                  installingId === selectedSkill.skill_id
                }
              >
                {installingId === selectedSkill.skill_id
                  ? '...'
                  : installedTitles.has(selectedSkill.title?.toLowerCase())
                    ? 'Installed'
                    : 'Install'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
