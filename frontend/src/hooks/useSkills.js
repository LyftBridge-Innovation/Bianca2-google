/**
 * useSkills hook — CRUD for per-user skill files.
 */
import { useState, useEffect, useCallback } from 'react';
import { getSkills, uploadSkill, deleteSkillAPI } from '../api/client';

export function useSkills(userId) {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSkills = useCallback(async () => {
    if (!userId) return;
    try {
      setLoading(true);
      const data = await getSkills(userId);
      setSkills(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch skills:', err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const upload = useCallback(async (file) => {
    if (!userId) return;
    const content = await file.text();
    const result = await uploadSkill(userId, file.name, content);
    setSkills(prev => [result, ...prev]);
    return result;
  }, [userId]);

  const deleteSkill = useCallback(async (skillId) => {
    if (!userId) return;
    await deleteSkillAPI(skillId, userId);
    setSkills(prev => prev.filter(s => s.skill_id !== skillId));
  }, [userId]);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  return { skills, loading, error, upload, deleteSkill, refreshSkills: fetchSkills };
}
