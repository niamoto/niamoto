import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  FolderOpen,
  Plus,
  Clock,
  ChevronRight,
  X,
  Settings2,
} from 'lucide-react';
import niamotoLogo from '@/assets/niamoto_logo.png';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { DesktopTitlebar } from '@/components/layout/DesktopTitlebar';
import type { ProjectEntry } from '@/shared/hooks/useProjectSwitcher';
import type { AppSettings } from '@/features/welcome/hooks/useWelcomeScreen';
import ProjectCreationWizard from './ProjectCreationWizard';

interface WelcomeScreenProps {
  recentProjects: ProjectEntry[];
  invalidProjects: Set<string>;
  settings: AppSettings;
  error?: string | null;
  onOpenProject: (path: string) => Promise<void>;
  onBrowseProject: () => Promise<string | null>;
  onCreateProject: (name: string, location: string) => Promise<string>;
  onRemoveProject: (path: string) => Promise<void>;
  onUpdateSettings: (settings: AppSettings) => Promise<void>;
  onBrowseFolder: () => Promise<string | null>;
}

export default function WelcomeScreen({
  recentProjects,
  invalidProjects,
  settings,
  error: externalError,
  onOpenProject,
  onBrowseProject,
  onCreateProject,
  onRemoveProject,
  onUpdateSettings,
  onBrowseFolder,
}: WelcomeScreenProps) {
  const { t } = useTranslation();
  const [showWizard, setShowWizard] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(externalError || null);

  useEffect(() => {
    setError(externalError ?? null);
  }, [externalError]);

  const handleOpenRecent = async (path: string) => {
    setLoading(path);
    setError(null);
    try {
      await onOpenProject(path);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open project');
    } finally {
      setLoading(null);
    }
  };

  const handleBrowse = async () => {
    setLoading('browse');
    setError(null);
    try {
      await onBrowseProject();
    } catch (err) {
      // User cancelled is not an error
      if (err instanceof Error && !err.message.includes('cancelled')) {
        setError(err.message);
      }
    } finally {
      setLoading(null);
    }
  };

  const handleRemoveProject = async (
    e: React.MouseEvent,
    path: string
  ) => {
    e.stopPropagation();
    try {
      await onRemoveProject(path);
    } catch (err) {
      console.error('Failed to remove project:', err);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return t('dates.today', 'Today');
    } else if (diffDays === 1) {
      return t('dates.yesterday', 'Yesterday');
    } else if (diffDays < 7) {
      return t('dates.days_ago', '{{count}} days ago', { count: diffDays });
    }

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  const truncatePath = (path: string, maxLength: number = 50) => {
    if (path.length <= maxLength) return path;
    const start = path.slice(0, 20);
    const end = path.slice(-27);
    return `${start}...${end}`;
  };

  const invalidRecentCount = recentProjects.filter((project) =>
    invalidProjects.has(project.path)
  ).length;
  const allRecentProjectsInvalid =
    recentProjects.length > 0 && invalidRecentCount === recentProjects.length;
  const showInvalidProjectsHint = invalidRecentCount > 0 && !error;

  if (showWizard) {
    return (
      <ProjectCreationWizard
        onComplete={onCreateProject}
        onCancel={() => setShowWizard(false)}
        onBrowseFolder={onBrowseFolder}
      />
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-background via-background to-muted/30">
      {/* Window titlebar with controls */}
      <DesktopTitlebar title="Niamoto" />

      {/* Main content - centered */}
      <div className="flex flex-1 flex-col items-center justify-center p-8">
        {/* Logo and Branding */}
        <div className="mb-12 text-center">
          <div className="mb-6 flex items-center justify-center">
            <img
              src={niamotoLogo}
              alt="Niamoto"
              className="h-32 w-auto object-contain"
            />
          </div>
          <h1 className="bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-4xl font-bold tracking-tight text-transparent dark:from-emerald-400 dark:to-teal-400">
            Niamoto
          </h1>
          <p className="mt-2 text-lg text-muted-foreground">
            {t('welcome.subtitle', 'Ecological Data Platform')}
          </p>
        </div>

        {/* Main Content */}
        <div className="flex w-full max-w-2xl flex-col gap-6">
          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          )}

          {showInvalidProjectsHint && (
            <div className="rounded-lg border border-amber-200/60 bg-amber-50/70 p-4 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
              {allRecentProjectsInvalid
                ? t(
                    'welcome.all_recent_projects_unavailable',
                    'Your recent projects are no longer available. Create a new project or open another folder to continue.'
                  )
                : t(
                    'welcome.some_recent_projects_unavailable',
                    'Some recent projects are no longer available. You can remove them from the list or open another folder.'
                  )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-4">
            <Button
              size="lg"
              className="btn-interactive h-28 flex-col gap-3 bg-gradient-to-br from-emerald-600 to-teal-600 text-white shadow-lg hover:from-emerald-700 hover:to-teal-700"
              onClick={() => setShowWizard(true)}
            >
              <Plus className="h-7 w-7" />
              <span className="font-medium">
                {t('welcome.create_project', 'Create New Project')}
              </span>
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="btn-interactive h-28 flex-col gap-3 border-2 hover:bg-muted/50"
              onClick={handleBrowse}
              disabled={loading === 'browse'}
            >
              <FolderOpen className="h-7 w-7" />
              <span className="font-medium">
                {t('welcome.open_project', 'Open Project')}
              </span>
            </Button>
          </div>

          {/* Recent Projects */}
          {recentProjects.length > 0 && (
            <Card className="border-muted/50 shadow-sm">
              <CardContent className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <h2 className="font-semibold">
                    {t('welcome.recent_projects', 'Recent Projects')}
                  </h2>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {recentProjects.length} {t('welcome.projects', 'projects')}
                  </span>
                </div>
                <div className="space-y-2">
                  {recentProjects.slice(0, 5).map((project) => {
                    const isInvalid = invalidProjects.has(project.path);

                    return (
                      <div
                        key={project.path}
                        className={cn(
                          'group flex items-center gap-2 rounded-lg border p-1 transition-colors',
                          isInvalid
                            ? 'border-amber-200/60 bg-amber-50/70 dark:border-amber-900/40 dark:bg-amber-950/20'
                            : 'border-transparent bg-muted/30 hover:bg-muted/60'
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => handleOpenRecent(project.path)}
                          disabled={loading === project.path || isInvalid}
                          className={cn(
                            'flex min-w-0 flex-1 items-center justify-between rounded-md p-2 text-left',
                            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
                            'disabled:cursor-not-allowed disabled:opacity-70'
                          )}
                        >
                          <div className="flex min-w-0 flex-col items-start gap-0.5 text-left">
                            <span className="truncate font-medium">
                              {project.name}
                            </span>
                            <span
                              className="font-mono text-xs text-muted-foreground"
                              title={project.path}
                            >
                              {truncatePath(project.path)}
                            </span>
                          </div>
                          <div className="ml-4 flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {isInvalid
                                ? t('welcome.unavailable', 'Unavailable')
                                : formatDate(project.last_accessed)}
                            </span>
                            {isInvalid ? (
                              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                            )}
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={(e) => handleRemoveProject(e, project.path)}
                          className={cn(
                            'rounded p-1 transition-all hover:bg-destructive/10 hover:text-destructive',
                            isInvalid ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                          )}
                          title={t('welcome.remove_from_list', 'Remove from list')}
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Settings */}
          <div className="flex items-center justify-between rounded-lg border border-muted/30 bg-muted/20 p-4">
            <div className="flex items-center gap-3">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <Label htmlFor="auto-load" className="cursor-pointer text-sm">
                {t('welcome.auto_load', 'Auto-load last project on startup')}
              </Label>
            </div>
            <Switch
              id="auto-load"
              checked={settings.auto_load_last_project}
              onCheckedChange={(checked) =>
                onUpdateSettings({ auto_load_last_project: checked })
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}
