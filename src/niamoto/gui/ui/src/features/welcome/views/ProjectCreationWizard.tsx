import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ChevronLeft,
  FolderOpen,
  Check,
  Loader2,
} from 'lucide-react';
import niamotoLogo from '@/assets/niamoto_logo.png';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DesktopTitlebar } from '@/components/layout/DesktopTitlebar';
import { getProjectNameValidationError } from '@/features/welcome/lib/projectNameValidation';

interface ProjectCreationWizardProps {
  onComplete: (name: string, location: string) => Promise<string>;
  onCancel: () => void;
  onBrowseFolder: () => Promise<string | null>;
}

interface WizardState {
  projectName: string;
  projectLocation: string;
  creating: boolean;
  error: string | null;
}

export default function ProjectCreationWizard({
  onComplete,
  onCancel,
  onBrowseFolder,
}: ProjectCreationWizardProps) {
  const { t } = useTranslation();
  const [state, setState] = useState<WizardState>({
    projectName: '',
    projectLocation: '',
    creating: false,
    error: null,
  });

  const updateState = (updates: Partial<WizardState>) => {
    setState((prev) => ({ ...prev, ...updates, error: null }));
  };

  const handleBrowse = async () => {
    const path = await onBrowseFolder();
    if (path) {
      updateState({ projectLocation: path });
    }
  };

  const validateForm = (): boolean => {
    if (!state.projectName.trim()) {
      updateState({ error: t('wizard.error.name_required', 'Project name is required') });
      return false;
    }
    if (!state.projectLocation.trim()) {
      updateState({ error: t('wizard.error.location_required', 'Location is required') });
      return false;
    }
    const nameError = getProjectNameValidationError(state.projectName);
    if (nameError) {
      updateState({
        error: t(`wizard.error.${nameError}`, 'Project name contains unsupported characters'),
      });
      return false;
    }
    return true;
  };

  const handleCreate = async () => {
    if (!validateForm()) {
      return;
    }

    updateState({ creating: true, error: null });

    try {
      await onComplete(state.projectName.trim(), state.projectLocation.trim());
      // Page will reload on success
    } catch (err) {
      updateState({
        creating: false,
        error: err instanceof Error ? err.message : 'Failed to create project',
      });
    }
  };

  const fullProjectPath = state.projectLocation
    ? `${state.projectLocation}/${state.projectName}`
    : '';

  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-background via-background to-muted/30">
      {/* Window titlebar with controls */}
      <DesktopTitlebar title="Niamoto - New Project" />

      {/* Main content */}
      <div className="flex-1 overflow-y-auto px-6 py-6 sm:px-8">
      <div className="mx-auto w-full max-w-xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-6 flex items-center justify-center">
          <img
            src={niamotoLogo}
            alt="Niamoto"
            className="h-32 w-auto object-contain"
          />
        </div>
          <h1 className="text-2xl font-bold">
            {t('wizard.title', 'Create New Project')}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {t('wizard.subtitle', 'Set up a new Niamoto project')}
          </p>
        </div>

        {/* Step Content */}
        <Card className="mb-6 border-muted/50 shadow-sm">
          <CardContent className="pt-6">
            <div className="space-y-6">
              {/* Project Name */}
              <div className="space-y-2">
                <Label htmlFor="project-name">
                  {t('wizard.project_name', 'Project Name')}
                </Label>
                <Input
                  id="project-name"
                  placeholder="my-ecological-project"
                  value={state.projectName}
                  onChange={(e) =>
                    updateState({ projectName: e.target.value })
                  }
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  autoFocus
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  {t(
                    'wizard.name_hint',
                    'This will be the folder name. Use letters, numbers, dashes, or underscores.'
                  )}
                </p>
              </div>

              {/* Project Location */}
              <div className="space-y-2">
                <Label htmlFor="project-location">
                  {t('wizard.project_location', 'Location')}
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="project-location"
                    placeholder="/Users/username/Projects"
                    value={state.projectLocation}
                    onChange={(e) =>
                      updateState({ projectLocation: e.target.value })
                    }
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    className="flex-1 font-mono"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleBrowse}
                    title={t('wizard.browse', 'Browse...')}
                  >
                    <FolderOpen className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t(
                    'wizard.location_hint',
                    'Parent directory where the project folder will be created'
                  )}
                </p>
              </div>

              {/* Preview Path */}
              {fullProjectPath && (
                <div className="rounded-lg bg-muted/30 p-4">
                  <p className="mb-1 text-xs text-muted-foreground">
                    {t('wizard.full_path', 'Full path')}:
                  </p>
                  <p className="text-sm font-mono break-all">
                    {fullProjectPath}
                  </p>
                </div>
              )}
            </div>

            {/* Error Message */}
            {state.error && (
              <div
                role="alert"
                className="mt-4 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
              >
                {state.error}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={onCancel} disabled={state.creating}>
            <ChevronLeft className="mr-2 h-4 w-4" />
            {t('actions.cancel', 'Cancel')}
          </Button>

          <Button
            onClick={handleCreate}
            disabled={state.creating}
            className="btn-interactive bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
          >
            {state.creating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('wizard.creating', 'Creating...')}
              </>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                {t('wizard.create', 'Create Project')}
              </>
            )}
          </Button>
        </div>
      </div>
      </div>
    </div>
  );
}
