import { type ReactNode } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { formatDistanceToNow } from "date-fns"
import { enUS, fr } from "date-fns/locale"
import { AlertTriangle, CheckCircle2, Circle, Loader2, RefreshCw } from "lucide-react"

import type { FreshnessStatus, StageStatus } from "@/hooks/usePipelineStatus"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface StageCardProps {
  icon: ReactNode
  title: string
  stage: StageStatus | undefined
  path: string
  borderColor: string
  iconBgClass: string
  actionLabel?: string
  onAction?: () => void
  children?: ReactNode
}

function StatusBadge({ status }: { status: FreshnessStatus }) {
  switch (status) {
    case "fresh":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case "stale":
      return <AlertTriangle className="h-4 w-4 text-amber-500" />
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
    case "never_run":
      return <Circle className="h-4 w-4 text-muted-foreground" />
    case "error":
      return <Circle className="h-4 w-4 text-muted-foreground" />
  }
}

export function StageCard({
  icon,
  title,
  stage,
  path,
  borderColor,
  iconBgClass,
  actionLabel,
  onAction,
  children,
}: StageCardProps) {
  const { t, i18n } = useTranslation("common")
  const navigate = useNavigate()
  const dateLocale = i18n.language === "fr" ? fr : enUS
  const status = stage?.status ?? "never_run"

  const timeAgo = stage?.last_run_at
    ? formatDistanceToNow(new Date(stage.last_run_at), {
        addSuffix: true,
        locale: dateLocale,
      })
    : null

  return (
    <Card
      className={cn(
        "cursor-pointer border-l-[3px] transition-colors hover:bg-accent/50",
        borderColor,
        status === "stale" &&
          "border-t-amber-300 border-r-amber-300 border-b-amber-300 dark:border-t-amber-800 dark:border-r-amber-800 dark:border-b-amber-800",
        status === "running" &&
          "border-t-blue-300 border-r-blue-300 border-b-blue-300 dark:border-t-blue-800 dark:border-r-blue-800 dark:border-b-blue-800",
      )}
      onClick={() => navigate(path)}
    >
      <CardHeader className="flex flex-row items-center gap-3 space-y-0 pb-2">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg",
            iconBgClass,
          )}
        >
          {icon}
        </div>
        <div className="flex-1">
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <StatusBadge status={status} />
      </CardHeader>
      <CardContent className="space-y-2">
        {children}

        {(timeAgo || stage?.last_job_duration_s) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {timeAgo && <span>{timeAgo}</span>}
            {stage?.last_job_duration_s && (
              <>
                <span>·</span>
                <span>
                  {t("pipeline.summary.built_in", "en {{seconds}}s", {
                    seconds: stage.last_job_duration_s,
                  })}
                </span>
              </>
            )}
          </div>
        )}

        {status === "never_run" && (
          <p className="text-xs text-muted-foreground">
            {t("pipeline.never_run", "Not yet run")}
          </p>
        )}

        {stage?.items && stage.items.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {stage.items.map((item) => (
              <span
                key={item.name}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
                  item.status === "fresh" &&
                    "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400",
                  item.status === "stale" &&
                    "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
                  item.status === "running" &&
                    "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
                  item.status === "never_run" &&
                    "bg-muted text-muted-foreground",
                )}
              >
                <StatusBadge status={item.status} />
                {item.name}
              </span>
            ))}
          </div>
        )}

        {status === "stale" && onAction && (
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
