import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
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
      return t('common.today', 'Today');
    } else if (diffDays === 1) {
      return t('common.yesterday', 'Yesterday');
    } else if (diffDays < 7) {
      return t('common.days_ago', '{{count}} days ago', { count: diffDays });
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
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-emerald-600 to-teal-600 dark:from-emerald-400 dark:to-teal-400 bg-clip-text text-transparent">
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
          <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-4">
          <Button
            size="lg"
            className="btn-interactive h-28 flex-col gap-3 bg-gradient-to-br from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white shadow-lg"
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
                {recentProjects.slice(0, 5).map((project) => (
                  <button
                    key={project.path}
                    onClick={() => handleOpenRecent(project.path)}
                    disabled={loading === project.path}
                    className={cn(
                      'group flex w-full items-center justify-between rounded-lg p-3',
                      'bg-muted/30 transition-all hover:bg-muted/60',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2'
                    )}
                  >
                    <div className="flex flex-col items-start gap-0.5 text-left">
                      <span className="font-medium">{project.name}</span>
                      <span
                        className="text-xs text-muted-foreground font-mono"
                        title={project.path}
                      >
                        {truncatePath(project.path)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {formatDate(project.last_accessed)}
                      </span>
                      <button
                        onClick={(e) => handleRemoveProject(e, project.path)}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-destructive/10 hover:text-destructive transition-all"
                        title={t('welcome.remove_from_list', 'Remove from list')}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                      <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                    </div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Settings */}
        <div className="flex items-center justify-between rounded-lg bg-muted/20 border border-muted/30 p-4">
          <div className="flex items-center gap-3">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            <Label htmlFor="auto-load" className="text-sm cursor-pointer">
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

        {/* Version */}
        <p className="mt-12 text-xs text-muted-foreground/60">
          {t('welcome.version', 'Version')} 0.7.4
        </p>
      </div>
      </div>
    </div>
  );
}
