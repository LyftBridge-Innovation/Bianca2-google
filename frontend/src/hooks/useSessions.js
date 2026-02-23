/**
 * useSessions hook - fetches and manages session list for sidebar.
 */
import { useState, useEffect, useCallback } from 'react';
import { getSessions } from '../api/client';

export function useSessions(userId) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSessions = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      const data = await getSessions(userId);
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
    sessions,
    loading,
    error,
    refreshSessions: fetchSessions,
  };
}
