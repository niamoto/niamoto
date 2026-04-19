import { useTranslation } from "react-i18next"
import { formatDistanceToNow } from "date-fns"
import { enUS, fr } from "date-fns/locale"
import { CheckCircle2, Database, Layers, Send } from "lucide-react"
import type { StageStatus } from "@/hooks/usePipelineStatus"

interface ActivityItem {
  type: "import" | "transform" | "export"
  last_run_at: string
  duration_s: number | null
}

function buildActivity(
  data: StageStatus | undefined,
  groups: StageStatus | undefined,
  publication: StageStatus | undefined,
): ActivityItem[] {
  const items: ActivityItem[] = []

  const add = (
    type: ActivityItem["type"],
    stage: StageStatus | undefined,
  ) => {
    if (
      stage?.last_run_at &&
      stage.status !== "never_run" &&
      stage.status !== "unconfigured"
    ) {
      items.push({
        type,
        last_run_at: stage.last_run_at,
        duration_s: stage.last_job_duration_s ?? null,
      })
    }
  }

  add("import", data)
  add("transform", groups)
  add("export", publication)

  // Tri anti-chronologique
  return items.sort(
    (a, b) =>
      new Date(b.last_run_at).getTime() - new Date(a.last_run_at).getTime(),
  )
}

const TYPE_CONFIG = {
  import: {
    icon: <Database className="h-3.5 w-3.5" />,
    label: "Import",
    bg: "bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400",
  },
  transform: {
    icon: <Layers className="h-3.5 w-3.5" />,
    label: "Recalcul",
    bg: "bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400",
  },
  export: {
    icon: <Send className="h-3.5 w-3.5" />,
    label: "Export",
    bg: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400",
  },
} as const

interface ActivityFeedProps {
  data: StageStatus | undefined
  groups: StageStatus | undefined
  publication: StageStatus | undefined
}

export function ActivityFeed({ data, groups, publication }: ActivityFeedProps) {
  const { t, i18n } = useTranslation("common")
  const dateLocale = i18n.language === "fr" ? fr : enUS

  const items = buildActivity(data, groups, publication)

  if (items.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        {t("pipeline.no_activity", "Aucune activité récente")}
      </p>
    )
  }

  return (
    <div className="divide-y divide-border/50">
      {items.map((item) => {
        const cfg = TYPE_CONFIG[item.type]
        const timeAgo = formatDistanceToNow(new Date(item.last_run_at), {
          addSuffix: true,
          locale: dateLocale,
        })

        return (
          <div key={item.type} className="flex items-start gap-2.5 py-2">
            <div
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md ${cfg.bg}`}
            >
              {cfg.icon}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium">{cfg.label}</span>
                <CheckCircle2 className="h-3 w-3 text-green-500" />
              </div>
              <p className="text-[11px] text-muted-foreground">
                {timeAgo}
                {item.duration_s != null && (
                  <span className="ml-1.5 opacity-70">· {item.duration_s}s</span>
                )}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
