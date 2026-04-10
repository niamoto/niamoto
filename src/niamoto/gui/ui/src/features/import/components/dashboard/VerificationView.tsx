import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, BarChart3, GitBranch, Map as MapIcon, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useImportSummaryDetailed } from '@/features/import/hooks/useImportSummaryDetailed'
import { DataCompletenessView } from './DataCompletenessView'
import { GeoCoverageView } from './GeoCoverageView'
import { TaxonomicConsistencyView } from './TaxonomicConsistencyView'
import { ValueValidationView } from './ValueValidationView'

type VerificationToolKey = 'completeness' | 'validation' | 'taxonomy' | 'coverage'

interface VerificationViewProps {
  initialTool?: VerificationToolKey
}

export function VerificationView({
  initialTool = 'completeness',
}: VerificationViewProps) {
  const { t } = useTranslation('sources')
  const { data: summary, isLoading, error } = useImportSummaryDetailed()
  const [activeTool, setActiveTool] = useState<VerificationToolKey>(initialTool)

  const tools = useMemo(
    () => [
      {
        key: 'completeness' as const,
        icon: BarChart3,
        title: t('dashboard.tools.fieldAvailability.title'),
        description: t('dashboard.tools.fieldAvailability.description'),
      },
      {
        key: 'validation' as const,
        icon: ShieldAlert,
        title: t('dashboard.tools.validation.title'),
        description: t('dashboard.tools.validation.description'),
      },
      {
        key: 'taxonomy' as const,
        icon: GitBranch,
        title: t('dashboard.tools.taxonomy.title'),
        description: t('dashboard.tools.taxonomy.description'),
      },
      {
        key: 'coverage' as const,
        icon: MapIcon,
        title: t('dashboard.tools.coverage.title'),
        description: t('dashboard.tools.coverage.description'),
      },
    ],
    [t]
  )

  const entities = summary?.entities ?? []
  const activeToolMeta = tools.find((tool) => tool.key === activeTool) ?? tools[0]

  const renderTool = () => {
    switch (activeTool) {
      case 'validation':
        return <ValueValidationView entities={entities} />
      case 'taxonomy':
        return <TaxonomicConsistencyView />
      case 'coverage':
        return <GeoCoverageView />
      case 'completeness':
      default:
        return <DataCompletenessView entities={entities} />
    }
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>{t('dashboard.errors.loadTitle')}</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : t('dashboard.errors.loadSummary')}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-auto p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t('dashboard.verification.title', 'Verification tools')}
          </h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {t(
              'dashboard.verification.description',
              'Run focused checks on imported data before building pages.'
            )}
          </p>
          <p className="text-xs text-muted-foreground">
            {t(
              'dashboard.verification.disclaimer',
              'These tools are diagnostics, not a single global quality score.'
            )}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {tools.map((tool) => {
            const Icon = tool.icon
            const active = activeTool === tool.key
            return (
              <Button
                key={tool.key}
                type="button"
                variant={active ? 'secondary' : 'outline'}
                onClick={() => setActiveTool(tool.key)}
                disabled={isLoading || entities.length === 0}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tool.title}
              </Button>
            )
          })}
        </div>

        <p className="max-w-3xl text-sm text-muted-foreground">
          {activeToolMeta.description}
        </p>

        {isLoading ? (
          <div className="text-sm text-muted-foreground">
            {t('tree.loading', 'Loading...')}
          </div>
        ) : entities.length === 0 ? (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {t(
                'dashboard.verification.noEntities',
                'No imported entities are available yet.'
              )}
            </AlertDescription>
          </Alert>
        ) : (
          renderTool()
        )}
      </div>
    </div>
  )
}
