import { useState, useEffect, useCallback } from 'react';
import { reloadDesktopProject } from '@/shared/desktop/projectReload';
import { markManualProjectOpen } from '@/shared/desktop/projectLaunchIntent';
import { invokeDesktop, isDesktopTauri } from '@/shared/desktop/tauri';

export interface ProjectEntry {
  path: string;
  name: string;
  last_accessed: string;
}

interface RecentProjectStatus {
  path: string;
  valid: boolean;
}

/**
 * Hook to manage project switching in desktop mode
 * Uses Tauri commands to interact with the Rust backend
 */
export function useProjectSwitcher() {
  const [storedCurrentProject, setStoredCurrentProject] = useState<string | null>(null);
  const [currentProject, setCurrentProject] = useState<string | null>(null);
  const [hasInvalidCurrentProject, setHasInvalidCurrentProject] = useState(false);
  const [recentProjects, setRecentProjects] = useState<ProjectEntry[]>([]);
  const [invalidProjects, setInvalidProjects] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if we're in Tauri environment
  const isTauri = isDesktopTauri();

  // Invoke Tauri command
  const invoke = useCallback(
    async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
      if (!isTauri) {
        throw new Error('Tauri commands only available in desktop mode');
      }
      return invokeDesktop<T>(cmd, args);
    },
    [isTauri]
  );

  // Load current project and recent projects
  const loadProjects = useCallback(async () => {
    if (!isTauri) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [current, recent, validationResults] = await Promise.all([
        invoke<string | null>('get_current_project'),
        invoke<ProjectEntry[]>('get_recent_projects'),
        invoke<RecentProjectStatus[]>('validate_recent_projects'),
      ]);

      const invalid = new Set(
        validationResults
          .filter((project) => !project.valid)
          .map((project) => project.path)
      );

      let currentProjectInvalid = false;
      if (current) {
        currentProjectInvalid = invalid.has(current);

        if (!currentProjectInvalid) {
          try {
            await invoke<boolean>('validate_project', { path: current });
          } catch {
            currentProjectInvalid = true;
            invalid.add(current);
          }
        }
      }

      setStoredCurrentProject(current);
      setHasInvalidCurrentProject(currentProjectInvalid);
      setInvalidProjects(invalid);
      setCurrentProject(currentProjectInvalid ? null : current);
      setRecentProjects(recent);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  }, [isTauri, invoke]);

  // Switch to a different project
  const switchProject = useCallback(
    async (projectPath: string) => {
      if (!isTauri) {
        throw new Error('Project switching only available in desktop mode');
      }

      try {
        setLoading(true);
        setError(null);

        if (invalidProjects.has(projectPath)) {
          throw new Error('This project is no longer available');
        }

        // Step 1: Save the new project to desktop config
        await invoke('set_current_project', { path: projectPath });

        // Step 2: Tell the FastAPI server to reload from desktop config
        await reloadDesktopProject({
          allowStates: ['loaded'],
          expectedProject: projectPath,
        });

        // Step 3: Reload the page to refresh the UI with new project data
        markManualProjectOpen(projectPath);
        window.location.reload();
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to switch project';
        setError(errorMsg);
        console.error('Failed to switch project:', err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [invalidProjects, isTauri, invoke]
  );

  // Remove a project from recent list
  const removeProject = useCallback(
    async (projectPath: string) => {
      if (!isTauri) {
        throw new Error('Project management only available in desktop mode');
      }

      try {
        await invoke('remove_recent_project', { path: projectPath });
        await loadProjects(); // Refresh the list
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to remove project';
        setError(errorMsg);
        console.error('Failed to remove project:', err);
        throw err;
      }
    },
    [isTauri, invoke, loadProjects]
  );

  // Validate a project path
  const validateProject = useCallback(
    async (projectPath: string): Promise<boolean> => {
      if (!isTauri) {
        return false;
      }

      try {
        return await invoke<boolean>('validate_project', { path: projectPath });
      } catch (err) {
        console.error('Failed to validate project:', err);
        return false;
      }
    },
    [isTauri, invoke]
  );

  // Browse for a project folder using native dialog
  const browseProject = useCallback(async (): Promise<string | null> => {
    if (!isTauri) {
      throw new Error('Project browsing only available in desktop mode');
    }

    try {
      const path = await invoke<string | null>('browse_project_folder');
      return path;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to browse project';
      setError(errorMsg);
      console.error('Failed to browse project:', err);
      throw err;
    }
  }, [isTauri, invoke]);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return {
    storedCurrentProject,
    currentProject,
    hasInvalidCurrentProject,
    recentProjects,
    invalidProjects,
    loading,
    error,
    isTauri,
    switchProject,
    removeProject,
    validateProject,
    browseProject,
    reload: loadProjects,
  };
}
