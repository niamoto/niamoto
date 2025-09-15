import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '@/lib/api-config';

interface ImportStatus {
  configured: boolean;
  executed: boolean;
  last_run: string | null;
  records_imported: number;
  config_file: string | null;
  data_sources: string[];
}

interface TransformStatus {
  configured: boolean;
  executed: boolean;
  last_run: string | null;
  groups: string[];
  config_file: string | null;
}

interface ExportStatus {
  configured: boolean;
  executed: boolean;
  last_run: string | null;
  exports: string[];
  config_file: string | null;
  static_site_exists: boolean;
}

export interface PipelineStatus {
  import_status: ImportStatus;
  transform: TransformStatus;
  export: ExportStatus;
  database_exists: boolean;
  database_path: string | null;
  project_name: string | null;
}

export function usePipelineStatus() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/status/`);
      if (!response.ok) {
        throw new Error('Failed to fetch pipeline status');
      }
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return {
    status,
    loading,
    error,
    refetch: fetchStatus,
  };
}

// Convenience hooks for specific status parts
export function useImportStatus() {
  const { status, loading, error, refetch } = usePipelineStatus();
  return {
    status: status?.import_status || null,
    loading,
    error,
    refetch,
  };
}

export function useTransformStatus() {
  const { status, loading, error, refetch } = usePipelineStatus();
  return {
    status: status?.transform || null,
    loading,
    error,
    refetch,
  };
}

export function useExportStatus() {
  const { status, loading, error, refetch } = usePipelineStatus();
  return {
    status: status?.export || null,
    loading,
    error,
    refetch,
  };
}

export function useDatabaseStatus() {
  const { status, loading, error, refetch } = usePipelineStatus();
  return {
    exists: status?.database_exists || false,
    path: status?.database_path || null,
    projectName: status?.project_name || null,
    loading,
    error,
    refetch,
  };
}
