import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { AlertTriangle, Database, Globe, Layers, Loader2, RefreshCw, Send } from "lucide-react"

import { usePipelineStatus } from "@/hooks/usePipelineStatus"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { StageCard } from "./StageCard"
import { DataSummary } from "./summaries/DataSummary"
import { CollectionsSummary } from "./summaries/CollectionsSummary"
import { SiteSummary } from "./summaries/SiteSummary"
import { PublicationSummary } from "./summaries/PublicationSummary"
import { CardEntrance, CardEntranceItem } from "@/components/motion/CardEntrance"

export function DashboardView() {
  const { t } = useTranslation("common")
  const navigate = useNavigate()
  const { data: pipeline } = usePipelineStatus()

  if (!pipeline) return null

  const hasStale =
    pipeline.data.status === "stale" ||
    pipeline.groups.status === "stale" ||
    pipeline.site.status === "stale" ||
    pipeline.publication.status === "stale"
  const hasPendingFirstRun =
    pipeline.groups.status === "never_run" ||
    pipeline.site.status === "never_run" ||
    pipeline.publication.status === "never_run"

  const staleGroups =
    pipeline.groups.items?.filter((item) => item.status === "stale") ?? []
  const neverRunGroups =
    pipeline.groups.items?.filter((item) => item.status === "never_run") ?? []

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">
            {t("pipeline.dashboard.title", "Dashboard")}
          </h1>
          {hasStale ? (
            <p className="text-amber-600 dark:text-amber-400">
              {t("pipeline.dashboard.stale_subtitle", "Updates are needed")}
            </p>
          ) : hasPendingFirstRun ? (
            <p className="text-muted-foreground">
              {t(
                "pipeline.dashboard.pending_subtitle",
                "Initial steps are still pending",
              )}
            </p>
          ) : (
            <p className="text-green-600 dark:text-green-400">
              {t(
                "pipeline.dashboard.fresh_subtitle",
                "Everything is up to date",
              )}
            </p>
          )}
        </div>

        {hasStale && (
          <Button
            className="gap-2"
            onClick={() => {
              if (pipeline.groups.status === "stale") navigate("/groups")
              else if (pipeline.site.status === "stale")
                navigate("/publish")
              else if (pipeline.publication.status === "stale")
                navigate("/publish?panel=destinations")
              else navigate("/sources/import")
            }}
          >
            <RefreshCw className="h-4 w-4" />
            {t("pipeline.dashboard.update_all", "Update")}
          </Button>
        )}
      </div>

      {staleGroups.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600 dark:text-amber-400" />
            <div className="flex-1">
              <p className="font-medium text-amber-800 dark:text-amber-300">
                {t("pipeline.cascade.title", "Update cascade")}
              </p>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-400">
                {t(
                  "pipeline.cascade.description",
                  "Recalculate {{count}} group(s) → Rebuild site → Publish",
                  { count: staleGroups.length },
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {!hasStale && neverRunGroups.length > 0 && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 dark:border-sky-900 dark:bg-sky-950/30">
          <div className="flex items-start gap-3">
            <RefreshCw className="mt-0.5 h-5 w-5 text-sky-600 dark:text-sky-400" />
            <div className="flex-1">
              <p className="font-medium text-sky-800 dark:text-sky-300">
                {t("pipeline.first_run.title", "First calculations")}
              </p>
              <p className="mt-1 text-sm text-sky-700 dark:text-sky-400">
                {t(
                  "pipeline.first_run.description",
                  "Calculate {{count}} collection(s) to initialize results before building and publishing.",
                  { count: neverRunGroups.length },
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      <CardEntrance className="grid gap-4 sm:grid-cols-2">
        <CardEntranceItem>
          <StageCard
            icon={<Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />}
            title={t("sidebar.nav.data", "Data")}
            stage={pipeline.data}
            path="/sources"
            borderColor="border-l-blue-500"
            iconBgClass="bg-blue-50 dark:bg-blue-950/40"
            actionLabel={t("pipeline.action_import", "Import")}
            onAction={() => navigate("/sources/import")}
          >
            <DataSummary summary={pipeline.data.summary} />
          </StageCard>
        </CardEntranceItem>

        <CardEntranceItem>
          <StageCard
            icon={<Layers className="h-5 w-5 text-amber-600 dark:text-amber-400" />}
            title={t("sidebar.nav.collections", "Collections")}
            stage={pipeline.groups}
            path="/groups"
            borderColor="border-l-amber-500"
            iconBgClass="bg-amber-50 dark:bg-amber-950/40"
            actionLabel={t("pipeline.action_recalculate", "Recalculate")}
            onAction={() => navigate("/groups")}
            showActionWhen={["stale", "never_run"]}
          >
            <CollectionsSummary
              status={pipeline.groups.status}
              groups={pipeline.groups.summary?.groups}
              items={
                pipeline.groups.items?.map((item) => ({
                  name: item.name,
                  status: item.status,
                })) ?? []
              }
            />
          </StageCard>
        </CardEntranceItem>

        <CardEntranceItem>
          <StageCard
            icon={<Globe className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
            title={t("sidebar.nav.site", "Site")}
            stage={pipeline.site}
            path="/site"
            borderColor="border-l-emerald-500"
            iconBgClass="bg-emerald-50 dark:bg-emerald-950/40"
            actionLabel={t("pipeline.action_configure", "Configure")}
            onAction={() => navigate("/site/pages")}
          >
            <SiteSummary summary={pipeline.site.summary} />
          </StageCard>
        </CardEntranceItem>

        <CardEntranceItem>
          <StageCard
            icon={<Send className="h-5 w-5 text-orange-600 dark:text-orange-400" />}
            title={t("sidebar.nav.publish", "Publish")}
            stage={pipeline.publication}
            path="/publish"
            borderColor="border-l-orange-500"
            iconBgClass="bg-orange-50 dark:bg-orange-950/40"
            actionLabel={t("pipeline.action_rebuild", "Rebuild")}
            onAction={() => navigate("/publish")}
          >
            <PublicationSummary summary={pipeline.publication.summary} />
          </StageCard>
        </CardEntranceItem>
      </CardEntrance>

      {pipeline.running_job && (
        <CardEntrance>
          <CardEntranceItem>
            <Card className="border-blue-200 dark:border-blue-800">
              <CardContent className="flex items-center gap-3 p-4">
                <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                <div className="flex-1">
                  <p className="font-medium">
                    {pipeline.running_job.type === "import" &&
                      t("pipeline.running_import", "Import en cours...")}
                    {pipeline.running_job.type === "transform" &&
                      t("pipeline.running_transform", "Calcul en cours...")}
                    {pipeline.running_job.type === "export" &&
                      t("pipeline.running_export", "Construction en cours...")}
                  </p>
                  {pipeline.running_job.message && (
                    <p className="text-sm text-muted-foreground">
                      {pipeline.running_job.message}
                    </p>
                  )}
                </div>
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  {pipeline.running_job.progress}%
                </span>
              </CardContent>
            </Card>
          </CardEntranceItem>
        </CardEntrance>
      )}
    </div>
  )
}
