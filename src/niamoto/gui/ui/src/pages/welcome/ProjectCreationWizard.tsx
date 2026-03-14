import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  Check,
  Loader2,
  Database,
  FileText,
  FolderTree,
  Settings,
} from 'lucide-react';
import niamotoLogo from '@/assets/niamoto_logo.png';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { DesktopTitlebar } from '@/components/layout/DesktopTitlebar';

interface ProjectCreationWizardProps {
  onComplete: (name: string, location: string) => Promise<string>;
  onCancel: () => void;
  onBrowseFolder: () => Promise<string | null>;
}

interface WizardState {
  step: number;
  projectName: string;
  projectLocation: string;
  creating: boolean;
  error: string | null;
}

const STEPS = [
  { id: 'details', title: 'Project Details' },
  { id: 'confirm', title: 'Confirmation' },
];

// Structure files to be created
const PROJECT_STRUCTURE = [
  { icon: Database, name: 'db/', description: 'Database storage (DuckDB)' },
  { icon: Settings, name: 'config/', description: 'Configuration files (YAML)' },
  { icon: FolderTree, name: 'imports/', description: 'Source data files' },
  { icon: FolderTree, name: 'exports/', description: 'Generated outputs' },
  { icon: FileText, name: 'logs/', description: 'Application logs' },
];

export default function ProjectCreationWizard({
  onComplete,
  onCancel,
  onBrowseFolder,
}: ProjectCreationWizardProps) {
  const { t } = useTranslation();
  const [state, setState] = useState<WizardState>({
    step: 0,
    projectName: '',
    projectLocation: '',
    creating: false,
    error: null,
  });

  const progress = ((state.step + 1) / STEPS.length) * 100;

  const updateState = (updates: Partial<WizardState>) => {
    setState((prev) => ({ ...prev, ...updates, error: null }));
  };

  const handleBrowse = async () => {
    const path = await onBrowseFolder();
    if (path) {
      updateState({ projectLocation: path });
    }
  };

  const validateStep = (): boolean => {
    if (state.step === 0) {
      if (!state.projectName.trim()) {
        updateState({ error: t('wizard.error.name_required', 'Project name is required') });
        return false;
      }
      if (!state.projectLocation.trim()) {
        updateState({ error: t('wizard.error.location_required', 'Location is required') });
        return false;
      }
      // Validate project name (no special characters except - and _)
      const nameRegex = /^[a-zA-Z0-9_-]+$/;
      if (!nameRegex.test(state.projectName.trim())) {
        updateState({
          error: t(
            'wizard.error.invalid_name',
            'Project name can only contain letters, numbers, dashes and underscores'
          ),
        });
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep()) {
      updateState({ step: state.step + 1 });
    }
  };

  const handleBack = () => {
    if (state.step === 0) {
      onCancel();
    } else {
      updateState({ step: state.step - 1 });
    }
  };

  const handleCreate = async () => {
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

      {/* Main content - centered */}
      <div className="flex flex-1 flex-col items-center justify-center p-8">
      <div className="w-full max-w-xl">
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

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="mb-3 flex justify-between px-2">
            {STEPS.map((step, index) => (
              <div
                key={step.id}
                className={cn(
                  'flex items-center gap-2 transition-colors',
                  index <= state.step
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-muted-foreground'
                )}
              >
                <div
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium',
                    index < state.step
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                      : index === state.step
                      ? 'bg-emerald-600/20 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
                  {index < state.step ? <Check className="h-3 w-3" /> : index + 1}
                </div>
                <span className="text-sm font-medium hidden sm:inline">
                  {t(`wizard.step.${step.id}`, step.title)}
                </span>
              </div>
            ))}
          </div>
          <Progress value={progress} className="h-1.5" />
        </div>

        {/* Step Content */}
        <Card className="mb-6 border-muted/50 shadow-sm">
          <CardContent className="pt-6">
            {state.step === 0 && (
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
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-xs text-muted-foreground mb-1">
                      {t('wizard.full_path', 'Full path')}:
                    </p>
                    <p className="text-sm font-mono break-all">
                      {fullProjectPath}
                    </p>
                  </div>
                )}
              </div>
            )}

            {state.step === 1 && (
              <div className="space-y-6">
                {/* Summary */}
                <div className="rounded-lg bg-muted/30 p-4">
                  <h3 className="mb-4 font-medium flex items-center gap-2">
                    <Check className="h-4 w-4 text-emerald-600" />
                    {t('wizard.review', 'Review your project')}
                  </h3>
                  <dl className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">
                        {t('wizard.name_label', 'Name')}:
                      </dt>
                      <dd className="font-medium font-mono">
                        {state.projectName}
                      </dd>
                    </div>
                    <div className="flex flex-col gap-1">
                      <dt className="text-muted-foreground">
                        {t('wizard.location_label', 'Location')}:
                      </dt>
                      <dd className="font-medium font-mono text-xs break-all">
                        {fullProjectPath}
                      </dd>
                    </div>
                  </dl>
                </div>

                {/* Structure Preview */}
                <div>
                  <p className="text-sm text-muted-foreground mb-3">
                    {t(
                      'wizard.will_create',
                      'The following structure will be created:'
                    )}
                  </p>
                  <div className="space-y-2">
                    {PROJECT_STRUCTURE.map((item) => (
                      <div
                        key={item.name}
                        className="flex items-center gap-3 rounded-lg bg-muted/20 p-2.5"
                      >
                        <item.icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <span className="font-mono text-sm">
                            {item.name}
                          </span>
                          <span className="text-xs text-muted-foreground ml-2">
                            {t(`wizard.structure.${item.name.replace('/', '')}`, item.description)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {state.error && (
              <div className="mt-4 rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
                {state.error}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={handleBack} disabled={state.creating}>
            <ChevronLeft className="mr-2 h-4 w-4" />
            {state.step === 0
              ? t('common.cancel', 'Cancel')
              : t('common.back', 'Back')}
          </Button>

          {state.step === 0 ? (
            <Button
              onClick={handleNext}
              className="btn-interactive bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
            >
              {t('common.next', 'Next')}
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
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
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
