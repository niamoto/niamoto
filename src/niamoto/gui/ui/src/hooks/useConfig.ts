import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '@/lib/api-config';

interface ConfigUpdate {
  content: Record<string, any>;
  backup?: boolean;
}

interface ConfigResponse {
  success: boolean;
  message: string;
  content?: Record<string, any>;
  backup_path?: string;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function useConfig(configName: 'import' | 'transform' | 'export' | 'config') {
  const [config, setConfig] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Fetch configuration
  const fetchConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/config/${configName}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch ${configName} configuration`);
      }
      const data = await response.json();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setConfig(null);
    } finally {
      setLoading(false);
    }
  }, [configName]);

  // Update configuration
  const updateConfig = useCallback(async (update: ConfigUpdate): Promise<ConfigResponse> => {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/config/${configName}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(update),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to update ${configName} configuration`);
      }

      const result: ConfigResponse = await response.json();

      // Update local state if successful
      if (result.success && result.content) {
        setConfig(result.content);
      }

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setSaving(false);
    }
  }, [configName]);

  // Validate configuration
  const validateConfig = useCallback(async (content: Record<string, any>): Promise<ValidationResult> => {
    try {
      const response = await fetch(`${API_BASE_URL}/config/${configName}/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(content),
      });

      if (!response.ok) {
        throw new Error(`Failed to validate ${configName} configuration`);
      }

      return await response.json();
    } catch (err) {
      return {
        valid: false,
        errors: [err instanceof Error ? err.message : 'Validation failed'],
        warnings: [],
      };
    }
  }, [configName]);

  // List backups
  const listBackups = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/config/${configName}/backup/list`);
      if (!response.ok) {
        throw new Error('Failed to list backups');
      }
      return await response.json();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return { backups: [] };
    }
  }, [configName]);

  // Restore from backup
  const restoreBackup = useCallback(async (backupFilename: string): Promise<ConfigResponse> => {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/config/${configName}/backup/restore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ backup_filename: backupFilename }),
      });

      if (!response.ok) {
        throw new Error('Failed to restore backup');
      }

      const result: ConfigResponse = await response.json();

      // Update local state if successful
      if (result.success && result.content) {
        setConfig(result.content);
      }

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setSaving(false);
    }
  }, [configName]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return {
    config,
    loading,
    error,
    saving,
    refetch: fetchConfig,
    updateConfig,
    validateConfig,
    listBackups,
    restoreBackup,
  };
}

// Hook for managing all pipeline configurations
export function usePipelineConfigs() {
  const importConfig = useConfig('import');
  const transformConfig = useConfig('transform');
  const exportConfig = useConfig('export');
  const mainConfig = useConfig('config');

  const loading = importConfig.loading || transformConfig.loading || exportConfig.loading || mainConfig.loading;
  const error = importConfig.error || transformConfig.error || exportConfig.error || mainConfig.error;

  return {
    import: importConfig,
    transform: transformConfig,
    export: exportConfig,
    config: mainConfig,
    loading,
    error,
  };
}
