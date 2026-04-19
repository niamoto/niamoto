import { useTranslation } from "react-i18next"
import type { TFunction } from "i18next"
import { formatDistanceToNow } from "date-fns"
import { enUS, fr } from "date-fns/locale"
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Circle,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { FreshnessStatus, StageStatus } from "@/hooks/usePipelineStatus"

interface PipelineStageProps {
  label: string
  stage: StageStatus | undefined
  entityLine: string | null
}

function statusConfig(status: FreshnessStatus) {
  switch (status) {
    case "fresh":
      return {
        icon: <CheckCircle2 className="h-4 w-4 text-green-500" />,
        dot: "bg-green-500",
        text: "text-green-700 dark:text-green-400",
        ring: "ring-border/60",
        bg: "bg-muted/30",
      }
    case "stale":
      return {
        icon: <AlertTriangle className="h-4 w-4 text-amber-500" />,
        dot: "bg-amber-500",
        text: "text-amber-600 dark:text-amber-400",
        ring: "ring-border/60",
        bg: "bg-muted/30",
      }
    case "running":
      return {
        icon: <Loader2 className="h-4 w-4 animate-spin text-blue-500" />,
        dot: "bg-blue-500 animate-pulse",
        text: "text-blue-600 dark:text-blue-400",
        ring: "ring-border/60",
        bg: "bg-muted/30",
      }
    default:
      return {
        icon: <Circle className="h-4 w-4 text-muted-foreground/50" />,
        dot: "bg-muted-foreground/30",
        text: "text-muted-foreground",
        ring: "ring-muted/30",
        bg: "bg-muted/20",
      }
  }
}

function PipelineStage({ label, stage, entityLine }: PipelineStageProps) {
  const { i18n } = useTranslation()
  const dateLocale = i18n.language === "fr" ? fr : enUS
  const status = stage?.status ?? "never_run"
  const cfg = statusConfig(status)

  const timeAgo = stage?.last_run_at
    ? formatDistanceToNow(new Date(stage.last_run_at), {
        addSuffix: true,
        locale: dateLocale,
      })
    : null

  return (
    <div
      className={cn(
        "flex flex-1 flex-col gap-1.5 rounded-xl px-4 py-3 ring-1",
        cfg.bg,
        cfg.ring,
      )}
    >
      <div className="flex items-center gap-2">
        {cfg.icon}
        <span className="text-sm font-semibold">{label}</span>
      </div>
      {entityLine && (
        <p className={cn("text-xs font-medium", cfg.text)}>{entityLine}</p>
      )}
      {timeAgo ? (
        <p className="text-xs text-muted-foreground">{timeAgo}</p>
      ) : (
        <p className="text-xs text-muted-foreground/60">—</p>
      )}
    </div>
  )
}

interface PipelineBarProps {
  data: StageStatus | undefined
  groups: StageStatus | undefined
  site: StageStatus | undefined
  publication: StageStatus | undefined
}

function entitySummaryLine(
  stage: StageStatus | undefined,
  t: TFunction,
  language: string,
): string | null {
  if (!stage?.summary) return null
  const s = stage.summary
  const locale = language === "fr" ? "fr-FR" : "en-US"

  // Data stage : total rows across all entities
  if (s.entities) {
    const total = s.entities.reduce((acc, e) => acc + e.row_count, 0)
    if (total === 0) return null
    const formatted = total.toLocaleString(locale)
    return t("pipeline.summary.rows", "{{count}} lignes", {
      count: total,
      formattedCount: formatted,
      defaultValue_one: "{{formattedCount}} ligne",
      defaultValue_other: "{{formattedCount}} lignes",
    })
  }

  // Groups stage : number of configured groups
  if (s.groups) {
    const count = s.groups.length
    if (count === 0) return null
    return t("pipeline.summary.groups", {
      count,
      defaultValue_one: "{{count}} groupe",
      defaultValue_other: "{{count}} groupes",
    })
  }

  // Site configured pages
  if (s.page_count != null) {
    return t("pipeline.summary.pages", {
      count: s.page_count,
      defaultValue_one: "{{count}} page",
      defaultValue_other: "{{count}} pages",
    })
  }

  // Published HTML pages
  if (s.html_page_count != null) {
    return t("pipeline.summary.pages", {
      count: s.html_page_count,
      defaultValue_one: "{{count}} page",
      defaultValue_other: "{{count}} pages",
    })
  }

  return null
}

export function PipelineBar({ data, groups, site, publication }: PipelineBarProps) {
  const { t, i18n } = useTranslation("common")

  return (
    <div className="flex items-center gap-2">
      <PipelineStage
        label={t("sidebar.nav.data", "Import")}
        stage={data}
        entityLine={entitySummaryLine(data, t, i18n.language)}
      />
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/40" />
      <PipelineStage
        label={t("sidebar.nav.collections", "Transform")}
        stage={groups}
        entityLine={entitySummaryLine(groups, t, i18n.language)}
      />
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/40" />
      <PipelineStage
        label={t("sidebar.nav.site", "Site")}
        stage={site}
        entityLine={entitySummaryLine(site, t, i18n.language)}
      />
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/40" />
      <PipelineStage
        label={t("sidebar.nav.publish", "Export")}
        stage={publication}
        entityLine={entitySummaryLine(publication, t, i18n.language)}
      />
    </div>
  )
}
