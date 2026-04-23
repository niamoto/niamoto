import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FolderOpen, Check, ChevronDown, X, AlertCircle, AlertTriangle, Plus } from 'lucide-react';
import { useProjectSwitcher } from '@/shared/hooks/useProjectSwitcher';
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
import { useProjectCreationStore } from '@/stores/projectCreationStore';

interface ProjectSwitcherProps {
  compact?: boolean;
  className?: string;
}

export function ProjectSwitcher({ compact = false, className }: ProjectSwitcherProps = {}) {
  const { t } = useTranslation();
  const {
    currentProject,
    recentProjects,
    invalidProjects,
    loading,
    error,
    switchProject,
    removeProject,
    browseProject,
  } = useProjectSwitcher();
  const openProjectCreation = useProjectCreationStore((state) => state.open);

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

  const triggerHoverClass =
    'text-foreground hover:!bg-muted/60 hover:!text-foreground data-[state=open]:!bg-muted/60 data-[state=open]:!text-foreground';
  const menuItemHoverClass =
    'hover:!bg-muted/60 hover:!text-foreground focus:!bg-muted/60 focus:!text-foreground data-[highlighted]:!bg-muted/60 data-[highlighted]:!text-foreground';
  const currentMenuItemClass =
    'bg-muted/90 text-foreground shadow-none border-border/70 hover:!bg-muted focus:!bg-muted data-[highlighted]:!bg-muted hover:!text-foreground focus:!text-foreground data-[highlighted]:!text-foreground';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {compact ? (
          <Button
            variant="outline"
            size="icon"
            className={cn(
              'h-9 w-9 mx-auto',
              triggerHoverClass,
              error && 'border-red-500',
              className
            )}
            disabled={switching}
            title={getProjectName(currentProject)}
          >
            <FolderOpen className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            variant="outline"
            className={cn(
              'w-full justify-between',
              triggerHoverClass,
              error && 'border-red-500',
              className
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
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align={compact ? 'start' : 'start'}
        side={compact ? 'right' : 'bottom'}
        className="w-[280px]"
      >
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
          recentProjects.map((project) => {
            const isInvalid = invalidProjects.has(project.path);
            const isCurrent = currentProject === project.path;

            return (
              <DropdownMenuItem
                key={project.path}
                onClick={() => {
                  if (!isInvalid) {
                    handleSwitchProject(project.path);
                  }
                }}
                className={cn(
                  'flex items-center justify-between gap-2 border border-transparent transition-colors',
                  isInvalid ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
                  isCurrent && !isInvalid && currentMenuItemClass,
                  !isCurrent && !isInvalid && menuItemHoverClass
                )}
              >
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="truncate text-sm font-medium">
                    {project.name}
                  </span>
                  <span
                    className={cn(
                      'truncate text-xs',
                      isCurrent && !isInvalid
                        ? 'text-foreground/70'
                        : 'text-muted-foreground'
                    )}
                  >
                    {project.path}
                  </span>
                </div>

                <div className="flex flex-shrink-0 items-center gap-1">
                  {isInvalid && (
                    <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                  )}
                  {!isInvalid && isCurrent && (
                    <Check className="h-4 w-4 text-foreground/70" />
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      'h-6 w-6 text-muted-foreground hover:!bg-muted/80 hover:!text-foreground',
                      isCurrent && !isInvalid && 'text-foreground/60',
                      isInvalid && 'opacity-100'
                    )}
                    onClick={(e) => handleRemoveProject(e, project.path)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </DropdownMenuItem>
            );
          })
        )}

        <DropdownMenuSeparator />

        <DropdownMenuItem
          className={cn('cursor-pointer', menuItemHoverClass)}
          onClick={() => openProjectCreation()}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t('project.create_new', 'Create New Project...')}
        </DropdownMenuItem>

        <DropdownMenuItem
          className={cn('cursor-pointer', menuItemHoverClass)}
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
