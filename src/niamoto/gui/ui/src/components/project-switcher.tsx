import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FolderOpen, Check, ChevronDown, X, AlertCircle } from 'lucide-react';
import { useProjectSwitcher } from '@/hooks/useProjectSwitcher';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

export function ProjectSwitcher() {
  const { t } = useTranslation();
  const {
    currentProject,
    recentProjects,
    loading,
    error,
    switchProject,
    removeProject,
    browseProject,
  } = useProjectSwitcher();

  const [switching, setSwitching] = useState(false);

  // Get display name from path (cross-platform)
  const getProjectName = (path: string | null) => {
    if (!path) return t('project.none_selected', 'No project');
    // Normalize backslashes to forward slashes and trim trailing slashes
    const normalized = path.replace(/\\/g, '/').replace(/\/+$/, '');
    // Split and filter out empty segments
    const parts = normalized.split('/').filter(segment => segment.length > 0);
    // Return last non-empty segment or fallback
    return parts.length > 0 ? parts[parts.length - 1] : t('project.none_selected', 'No project');
  };

  const handleSwitchProject = async (path: string) => {
    try {
      setSwitching(true);
      await switchProject(path);
    } catch (err) {
      console.error('Failed to switch project:', err);
      setSwitching(false);
    }
  };

  const handleRemoveProject = async (
    e: React.MouseEvent,
    path: string
  ) => {
    e.stopPropagation(); // Prevent menu item click
    try {
      await removeProject(path);
    } catch (err) {
      console.error('Failed to remove project:', err);
    }
  };

  if (loading && !currentProject) {
    return null; // Don't show while initially loading
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-[200px] justify-between',
            error && 'border-red-500'
          )}
          disabled={switching}
        >
          <div className="flex items-center gap-2 overflow-hidden">
            <FolderOpen className="h-4 w-4 flex-shrink-0" />
            <span className="truncate text-sm">
              {switching
                ? t('project.switching', 'Switching...')
                : getProjectName(currentProject)}
            </span>
          </div>
          <ChevronDown className="h-4 w-4 flex-shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-[280px]">
        <DropdownMenuLabel>
          {t('project.recent_projects', 'Recent Projects')}
        </DropdownMenuLabel>

        {error && (
          <div className="px-2 py-2 text-sm text-red-500 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span className="text-xs">{error}</span>
          </div>
        )}

        <DropdownMenuSeparator />

        {recentProjects.length === 0 ? (
          <div className="px-2 py-6 text-center text-sm text-muted-foreground">
            {t('project.no_recent', 'No recent projects')}
          </div>
        ) : (
          recentProjects.map((project) => (
            <DropdownMenuItem
              key={project.path}
              onClick={() => handleSwitchProject(project.path)}
              className="flex items-center justify-between gap-2 cursor-pointer"
            >
              <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                <span className="text-sm font-medium truncate">
                  {project.name}
                </span>
                <span className="text-xs text-muted-foreground truncate">
                  {project.path}
                </span>
              </div>

              <div className="flex items-center gap-1 flex-shrink-0">
                {currentProject === project.path && (
                  <Check className="h-4 w-4 text-primary" />
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={(e) => handleRemoveProject(e, project.path)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </DropdownMenuItem>
          ))
        )}

        <DropdownMenuSeparator />

        <DropdownMenuItem
          className="cursor-pointer"
          onClick={async () => {
            try {
              const path = await browseProject();
              if (path) {
                await handleSwitchProject(path);
              }
            } catch (err) {
              console.error('Failed to browse or switch project:', err);
            }
          }}
        >
          <FolderOpen className="mr-2 h-4 w-4" />
          {t('project.open_other', 'Open Other Project...')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
