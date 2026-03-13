/**
 * ProjectHub — Adaptive dashboard showing pipeline status at a glance.
 *
 * Three states:
 * - Empty project → onboarding checklist
 * - Everything fresh → calm status overview
 * - Something stale → prominent warnings with cascade actions
 *
 * Route: /
 */

import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePipelineStatus, type StageStatus, type FreshnessStatus, type StageSummary } from '@/hooks/usePipelineStatus'
import { useImportSummary } from '@/hooks/useImportSummary'
import { useDatasets } from '@/hooks/useDatasets'
import { useReferences } from '@/hooks/useReferences'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import {
  Database,
  Layers,
  Globe,
  Send,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Circle,
  Loader2,
  RefreshCw,
  Upload,
  FileText,
  Languages,
  Package,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { fr, enUS } from 'date-fns/locale'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Stage card component
// ---------------------------------------------------------------------------

interface StageCardProps {
  icon: React.ReactNode
  title: string
  stage: StageStatus | undefined
  path: string
  borderColor: string
  iconBgClass: string
  actionLabel?: string
  onAction?: () => void
  children?: React.ReactNode
}

function StatusBadge({ status }: { status: FreshnessStatus }) {
  switch (status) {
    case 'fresh':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case 'stale':
      return <AlertTriangle className="h-4 w-4 text-amber-500" />
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
    case 'never_run':
      return <Circle className="h-4 w-4 text-muted-foreground" />
    default:
      return <Circle className="h-4 w-4 text-muted-foreground" />
  }
}

function StageCard({ icon, title, stage, path, borderColor, iconBgClass, actionLabel, onAction, children }: StageCardProps) {
  const { t, i18n } = useTranslation('common')
  const navigate = useNavigate()
  const dateLocale = i18n.language === 'fr' ? fr : enUS
  const status = stage?.status ?? 'never_run'

  const timeAgo = stage?.last_run_at
    ? formatDistanceToNow(new Date(stage.last_run_at), { addSuffix: true, locale: dateLocale })
    : null

  return (
    <Card
      className={cn(
        'cursor-pointer border-l-[3px] transition-colors hover:bg-accent/50',
        borderColor,
        status === 'stale' && 'border-t-amber-300 border-r-amber-300 border-b-amber-300 dark:border-t-amber-800 dark:border-r-amber-800 dark:border-b-amber-800',
        status === 'running' && 'border-t-blue-300 border-r-blue-300 border-b-blue-300 dark:border-t-blue-800 dark:border-r-blue-800 dark:border-b-blue-800',
      )}
      onClick={() => navigate(path)}
    >
      <CardHeader className="flex flex-row items-center gap-3 space-y-0 pb-2">
        <div className={cn('flex h-9 w-9 items-center justify-center rounded-lg', iconBgClass)}>
          {icon}
        </div>
        <div className="flex-1">
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <StatusBadge status={status} />
      </CardHeader>
      <CardContent className="space-y-2">
        {children}

        {/* Timestamp + duration on same line */}
        {(timeAgo || stage?.last_job_duration_s) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {timeAgo && <span>{timeAgo}</span>}
            {stage?.last_job_duration_s && (
              <>
                <span>·</span>
                <span>{t('pipeline.summary.built_in', 'en {{seconds}}s', { seconds: stage.last_job_duration_s })}</span>
              </>
            )}
          </div>
        )}

        {status === 'never_run' && (
          <p className="text-xs text-muted-foreground">{t('pipeline.never_run', 'Pas encore exécuté')}</p>
        )}

        {/* Group items detail */}
        {stage?.items && stage.items.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {stage.items.map((item) => (
              <span
                key={item.name}
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs',
                  item.status === 'fresh' && 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400',
                  item.status === 'stale' && 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400',
                  item.status === 'running' && 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400',
                  item.status === 'never_run' && 'bg-muted text-muted-foreground',
                )}
              >
                <StatusBadge status={item.status} />
                {item.name}
              </span>
            ))}
          </div>
        )}

        {status === 'stale' && onAction && (
          <Button
            size="sm"
            variant="outline"
            className="mt-2 h-7 gap-1.5 text-xs"
            onClick={(e) => {
              e.stopPropagation()
              onAction()
            }}
          >
            <RefreshCw className="h-3 w-3" />
            {actionLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Summary info components for each stage card
// ---------------------------------------------------------------------------

function DataSummary({ summary }: { summary: StageSummary | null }) {
  const { t } = useTranslation('common')
  const navigate = useNavigate()
  const { data: importSummary } = useImportSummary()

  if (!summary?.entities?.length) return null

  const qualityPercent = importSummary ? Math.round(importSummary.quality_score * 100) : null
  const alertCount = importSummary?.alert_count ?? 0

  return (
    <div className="space-y-2">
      {/* Entity chips with row counts */}
      <div className="flex flex-wrap gap-1.5">
        {summary.entities.map((e) => (
          <span
            key={e.name}
            className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-0.5 text-xs"
          >
            <span className="font-medium">{e.name}</span>
            <span className="text-muted-foreground">{e.row_count.toLocaleString()}</span>
          </span>
        ))}
      </div>

      {/* Quality bar + alerts */}
      {qualityPercent != null && (
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              {t('pipeline.summary.quality', 'Qualité {{score}}%', { score: qualityPercent })}
            </span>
            {alertCount > 0 && (
              <button
                className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-400 dark:hover:bg-amber-950"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate('/sources')
                }}
              >
                <AlertTriangle className="h-3 w-3" />
                {alertCount === 1
                  ? t('pipeline.summary.alert', '1 alerte')
                  : t('pipeline.summary.alerts', '{{count}} alertes', { count: alertCount })
                }
              </button>
            )}
          </div>
          <Progress
            value={qualityPercent}
            className={`h-1.5 ${
              qualityPercent >= 90
                ? '[&>div]:bg-green-500'
                : qualityPercent >= 70
                  ? '[&>div]:bg-yellow-500'
                  : '[&>div]:bg-red-500'
            }`}
          />
        </div>
      )}
    </div>
  )
}

function GroupsSummary({ items }: { items: Array<{ name: string; status: FreshnessStatus }> }) {
  const { t } = useTranslation('common')
  if (!items?.length) return null

  const freshCount = items.filter((i) => i.status === 'fresh').length
  const total = items.length
  const allFresh = freshCount === total
  const staleCount = total - freshCount

  return (
    <p className={cn(
      'text-xs',
      allFresh ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400',
    )}>
      {allFresh
        ? t('pipeline.summary.groups_ratio', '{{fresh}}/{{total}} à jour', { fresh: freshCount, total })
        : t('pipeline.summary.groups_stale_ratio', '{{stale}}/{{total}} à recalculer', { stale: staleCount, total })
      }
    </p>
  )
}

function SiteSummary({ summary }: { summary: StageSummary | null }) {
  const { t } = useTranslation('common')
  if (!summary) return null

  const parts: string[] = []
  if ((summary.page_count ?? 0) > 0) {
    parts.push(t('pipeline.summary.pages', '{{count}} pages', { count: summary.page_count }))
  }
  if ((summary.language_count ?? 0) > 1 && summary.languages) {
    parts.push(summary.languages.join(', '))
  }

  return (
    <div className="space-y-1">
      {summary.title && (
        <p className="text-sm font-medium">{summary.title}</p>
      )}
      {parts.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {parts.join(' · ')}
        </p>
      )}
    </div>
  )
}

function PublicationSummary({ summary }: { summary: StageSummary | null }) {
  const { t } = useTranslation('common')
  if (!summary?.html_page_count) return null

  const parts: string[] = [
    t('pipeline.summary.html_pages', '{{count}} pages HTML', { count: summary.html_page_count }),
  ]
  if ((summary.total_size_mb ?? 0) > 0) {
    parts.push(`${summary.total_size_mb} MB`)
  }

  return (
    <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <Package className="h-3 w-3" />
      {parts.join(' · ')}
    </p>
  )
}

// ---------------------------------------------------------------------------
// Onboarding checklist (empty project)
// ---------------------------------------------------------------------------

function OnboardingView() {
  const { t } = useTranslation('common')
  const navigate = useNavigate()

  const steps = [
    {
      number: 1,
      title: t('pipeline.onboarding.step1', 'Importer vos données'),
      description: t('pipeline.onboarding.step1_desc', 'Fichiers CSV, taxonomie, shapefile'),
      path: '/sources/import',
      icon: <Upload className="h-5 w-5" />,
    },
    {
      number: 2,
      title: t('pipeline.onboarding.step2', 'Configurer les groupes'),
      description: t('pipeline.onboarding.step2_desc', 'Choisir les widgets et statistiques à calculer'),
      path: '/groups',
      icon: <Layers className="h-5 w-5" />,
    },
    {
      number: 3,
      title: t('pipeline.onboarding.step3', 'Personnaliser le site'),
      description: t('pipeline.onboarding.step3_desc', 'Pages, navigation, apparence'),
      path: '/site',
      icon: <Globe className="h-5 w-5" />,
    },
    {
      number: 4,
      title: t('pipeline.onboarding.step4', 'Publier'),
      description: t('pipeline.onboarding.step4_desc', 'Construire et déployer le site web'),
      path: '/publish',
      icon: <Send className="h-5 w-5" />,
    },
  ]

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">{t('pipeline.onboarding.title', 'Bienvenue sur Niamoto')}</h1>
        <p className="mt-2 text-muted-foreground">
          {t('pipeline.onboarding.subtitle', 'Suivez ces étapes pour configurer votre portail de données écologiques.')}
        </p>
      </div>

      <div className="space-y-3">
        {steps.map((step) => (
          <Card
            key={step.number}
            className="cursor-pointer transition-colors hover:bg-accent/50"
            onClick={() => navigate(step.path)}
          >
            <CardContent className="flex items-center gap-4 p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-bold text-muted-foreground">
                {step.number}
              </div>
              <div className="flex-1">
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">{step.description}</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground">
                {step.icon}
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main hub (project has data)
// ---------------------------------------------------------------------------

function DashboardView() {
  const { t } = useTranslation('common')
  const navigate = useNavigate()
  const { data: pipeline } = usePipelineStatus()

  if (!pipeline) return null

  const hasStale = pipeline.data.status === 'stale'
    || pipeline.groups.status === 'stale'
    || pipeline.site.status === 'stale'
    || pipeline.publication.status === 'stale'

  const staleGroups = pipeline.groups.items?.filter(i => i.status === 'stale' || i.status === 'never_run') ?? []

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('pipeline.dashboard.title', 'Tableau de bord')}</h1>
          {hasStale ? (
            <p className="text-amber-600 dark:text-amber-400">
              {t('pipeline.dashboard.stale_subtitle', 'Des mises à jour sont nécessaires')}
            </p>
          ) : (
            <p className="text-green-600 dark:text-green-400">
              {t('pipeline.dashboard.fresh_subtitle', 'Tout est à jour')}
            </p>
          )}
        </div>

        {hasStale && (
          <Button
            className="gap-2"
            onClick={() => {
              if (pipeline.groups.status === 'stale') navigate('/groups')
              else if (pipeline.site.status === 'stale') navigate('/publish/build')
              else if (pipeline.publication.status === 'stale') navigate('/publish/deploy')
              else navigate('/sources/import')
            }}
          >
            <RefreshCw className="h-4 w-4" />
            {t('pipeline.dashboard.update_all', 'Mettre à jour')}
          </Button>
        )}
      </div>

      {/* Cascade banner when groups are stale */}
      {staleGroups.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600 dark:text-amber-400" />
            <div className="flex-1">
              <p className="font-medium text-amber-800 dark:text-amber-300">
                {t('pipeline.cascade.title', 'Cascade de mises à jour')}
              </p>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-400">
                {t('pipeline.cascade.description', 'Recalculer {{count}} groupe(s) → Reconstruire le site → Publier', { count: staleGroups.length })}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stage cards grid */}
      <div className="grid gap-4 sm:grid-cols-2">
        <StageCard
          icon={<Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />}
          title={t('sidebar.nav.data', 'Données')}
          stage={pipeline.data}
          path="/sources"
          borderColor="border-l-blue-500"
          iconBgClass="bg-blue-50 dark:bg-blue-950/40"
          actionLabel={t('pipeline.action_import', 'Importer')}
          onAction={() => navigate('/sources/import')}
        >
          <DataSummary summary={pipeline.data.summary} />
        </StageCard>

        <StageCard
          icon={<Layers className="h-5 w-5 text-amber-600 dark:text-amber-400" />}
          title={t('sidebar.nav.groups', 'Groupes')}
          stage={pipeline.groups}
          path="/groups"
          borderColor="border-l-amber-500"
          iconBgClass="bg-amber-50 dark:bg-amber-950/40"
          actionLabel={t('pipeline.action_recalculate', 'Recalculer')}
          onAction={() => navigate('/groups')}
        >
          <GroupsSummary items={pipeline.groups.items?.map(i => ({ name: i.name, status: i.status })) ?? []} />
        </StageCard>

        <StageCard
          icon={<Globe className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
          title={t('sidebar.nav.site', 'Site')}
          stage={pipeline.site}
          path="/site"
          borderColor="border-l-emerald-500"
          iconBgClass="bg-emerald-50 dark:bg-emerald-950/40"
          actionLabel={t('pipeline.action_configure', 'Configurer')}
          onAction={() => navigate('/site/pages')}
        >
          <SiteSummary summary={pipeline.site.summary} />
        </StageCard>

        <StageCard
          icon={<Send className="h-5 w-5 text-orange-600 dark:text-orange-400" />}
          title={t('sidebar.nav.publish', 'Publication')}
          stage={pipeline.publication}
          path="/publish"
          borderColor="border-l-orange-500"
          iconBgClass="bg-orange-50 dark:bg-orange-950/40"
          actionLabel={t('pipeline.action_rebuild', 'Reconstruire')}
          onAction={() => navigate('/publish/build')}
        >
          <PublicationSummary summary={pipeline.publication.summary} />
        </StageCard>
      </div>

      {/* Running job indicator */}
      {pipeline.running_job && (
        <Card className="border-blue-200 dark:border-blue-800">
          <CardContent className="flex items-center gap-3 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            <div className="flex-1">
              <p className="font-medium">
                {pipeline.running_job.type === 'import' && t('pipeline.running_import', 'Import en cours...')}
                {pipeline.running_job.type === 'transform' && t('pipeline.running_transform', 'Calcul en cours...')}
                {pipeline.running_job.type === 'export' && t('pipeline.running_export', 'Construction en cours...')}
              </p>
              {pipeline.running_job.message && (
                <p className="text-sm text-muted-foreground">{pipeline.running_job.message}</p>
              )}
            </div>
            <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
              {pipeline.running_job.progress}%
            </span>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root export
// ---------------------------------------------------------------------------

export default function ProjectHub() {
  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets()
  const { data: referencesData, isLoading: referencesLoading } = useReferences()
  const { isLoading: projectLoading } = useProjectInfo()

  const isLoading = datasetsLoading || referencesLoading || projectLoading

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const datasets = datasetsData?.datasets ?? []
  const references = referencesData?.references ?? []
  const hasData = datasets.length > 0 || references.length > 0

  if (!hasData) {
    return <OnboardingView />
  }

  return <DashboardView />
}
