import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { usePipelineStatus } from "@/hooks/usePipelineStatus"
import { PipelineBar } from "./PipelineBar"
import { QuickActions } from "./QuickActions"
import { KeyStats } from "./KeyStats"
import { ActivityFeed } from "./ActivityFeed"

export function DashboardView() {
  const { t } = useTranslation("common")
  const { data: pipeline, isLoading, isFetching } = usePipelineStatus()

  if (!pipeline) {
    if (!isLoading) return null
    return (
      <div className="flex h-full items-center justify-center p-4">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>{t("pipeline.dashboard.loading", "Chargement du tableau de bord...")}</span>
        </div>
      </div>
    )
  }

  const { data, groups, site, publication, running_job } = pipeline

  // Statut global résumé en une ligne
  const allFresh =
    data.status === "fresh" &&
    (groups.status === "fresh" || groups.status === "unconfigured") &&
    publication.status !== "stale"

  const hasStale =
    data.status === "stale" ||
    groups.status === "stale" ||
    publication.status === "stale"

  const globalLabel = running_job
    ? t("pipeline.dashboard.running", "Pipeline en cours d'exécution")
    : allFresh
      ? t("pipeline.dashboard.fresh_subtitle", "Tout est à jour")
      : hasStale
        ? t("pipeline.dashboard.stale_subtitle", "Des mises à jour sont nécessaires")
        : t("pipeline.dashboard.pending_subtitle", "Étapes initiales en attente")

  const globalColor = running_job
    ? "text-blue-600 dark:text-blue-400"
    : allFresh
      ? "text-green-600 dark:text-green-400"
      : hasStale
        ? "text-amber-600 dark:text-amber-400"
        : "text-muted-foreground"

  return (
    <div className="flex flex-col gap-5 p-4 pb-6">
      {/* ── En-tête ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">
            {t("pipeline.dashboard.title", "Dashboard")}
          </h1>
          <p className={globalColor}>{globalLabel}</p>
        </div>
        {isFetching && !running_job && (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/50" />
        )}
      </div>

      {/* ── Job en cours ─────────────────────────────────────────── */}
      {running_job && (
        <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20">
          <CardContent className="flex items-center gap-3 p-4">
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-blue-500" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {running_job.type === "import" &&
                  t("pipeline.running_import", "Import en cours...")}
                {running_job.type === "transform" &&
                  t("pipeline.running_transform", "Calcul en cours...")}
                {running_job.type === "export" &&
                  t("pipeline.running_export", "Construction en cours...")}
              </p>
              {running_job.message && (
                <p className="truncate text-xs text-muted-foreground">
                  {running_job.message}
                </p>
              )}
              <Progress
                value={running_job.progress}
                className="mt-2 h-1.5"
              />
            </div>
            <span className="shrink-0 text-sm font-semibold tabular-nums text-blue-600 dark:text-blue-400">
              {running_job.progress}%
            </span>
          </CardContent>
        </Card>
      )}

      {/* ── Barre pipeline ──────────────────────────────────────── */}
      <PipelineBar
        data={data}
        groups={groups}
        publication={publication}
      />

      {/* ── Actions rapides ─────────────────────────────────────── */}
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("pipeline.quick_actions", "Actions rapides")}
        </p>
        <QuickActions
          dataStatus={data.status}
          groupsStatus={groups.status}
          siteStatus={site.status}
          publicationStatus={publication.status}
          isRunning={!!running_job}
        />
      </div>

      {/* ── Bas : Stats + Activité ──────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm font-semibold">
              {t("pipeline.key_stats", "Données")}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 pt-0">
            <KeyStats
              dataSummary={data.summary}
              groupsSummary={groups.summary}
              siteSummary={site.summary}
              pubSummary={publication.summary}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm font-semibold">
              {t("pipeline.recent_activity", "Activité récente")}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 pt-0">
            <ActivityFeed />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
