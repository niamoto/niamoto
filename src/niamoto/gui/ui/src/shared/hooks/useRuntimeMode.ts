import { useState, useEffect } from 'react';

interface RuntimeMode {
  mode: 'desktop' | 'web';
  project: string | null;
  features: {
    project_switching: boolean;
  };
}

/**
 * Hook to detect runtime mode (desktop vs web)
 * Fetches from /api/health/runtime-mode to determine if running in Tauri
 */
export function useRuntimeMode() {
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>({
    mode: 'web',
    project: null,
    features: { project_switching: false },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRuntimeMode = async () => {
      try {
        const response = await fetch('/api/health/runtime-mode');
        if (!response.ok) {
          throw new Error('Failed to fetch runtime mode');
        }
        const data = await response.json();
        setRuntimeMode(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        console.error('Failed to fetch runtime mode:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchRuntimeMode();
  }, []);

  return {
    ...runtimeMode,
    loading,
    error,
    isDesktop: runtimeMode.mode === 'desktop',
    isWeb: runtimeMode.mode === 'web',
  };
}
