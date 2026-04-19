import { useTranslation } from "react-i18next"
import { Database, Layers, Map } from "lucide-react"
import { cn } from "@/lib/utils"
import type { StageSummary } from "@/hooks/usePipelineStatus"

interface StatRowProps {
  icon: React.ReactNode
  label: string
  value: string | number
  sub?: string
  highlight?: boolean
}

function StatRow({ icon, label, value, sub, highlight }: StatRowProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-right">
        <span
          className={cn(
            "text-sm font-semibold tabular-nums",
            highlight && "text-foreground",
          )}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
        {sub && (
          <span className="ml-1.5 text-xs text-muted-foreground">{sub}</span>
        )}
      </div>
    </div>
  )
}

interface KeyStatsProps {
  dataSummary: StageSummary | null | undefined
  groupsSummary: StageSummary | null | undefined
  siteSummary: StageSummary | null | undefined
  pubSummary: StageSummary | null | undefined
}

export function KeyStats({
  dataSummary,
  groupsSummary,
  siteSummary,
  pubSummary,
}: KeyStatsProps) {
  const { t } = useTranslation("common")

  const entities = dataSummary?.entities ?? []
  const groups = groupsSummary?.groups ?? []
  const htmlPageCount = pubSummary?.html_page_count ?? null
  const totalSizeMb = pubSummary?.total_size_mb ?? null

  // Total lignes tous types confondus
  const totalRows = entities.reduce((acc, e) => acc + e.row_count, 0)

  const hasAny = totalRows > 0 || groups.length > 0

  if (!hasAny) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        {t("pipeline.no_data_yet", "Aucune donnée importée")}
      </p>
    )
  }

  return (
    <div className="divide-y divide-border/50">
      {/* Entités importées */}
      {entities.map((entity) => (
        <StatRow
          key={entity.name}
          icon={<Database className="h-3.5 w-3.5" />}
          label={entity.name}
          value={entity.row_count}
          sub={t("pipeline.rows", "lignes")}
          highlight={entity.row_count > 0}
        />
      ))}

      {/* Groupes */}
      {groups.length > 0 && (
        <StatRow
          icon={<Layers className="h-3.5 w-3.5" />}
          label={t("sidebar.nav.collections", "Collections")}
          value={groups.length}
          sub={t("pipeline.groups_unit", "groupes")}
          highlight
        />
      )}

      {/* Site */}
      {siteSummary?.page_count != null && siteSummary.page_count > 0 && (
        <StatRow
          icon={<Map className="h-3.5 w-3.5" />}
          label={t("sidebar.nav.site", "Site")}
          value={siteSummary.page_count}
          sub={t("pipeline.pages_unit", "pages configurées")}
        />
      )}

      {/* Publication */}
      {htmlPageCount != null && (
        <StatRow
          icon={<Map className="h-3.5 w-3.5" />}
          label={t("sidebar.nav.publish", "Publication")}
          value={htmlPageCount}
          sub={
            totalSizeMb != null
              ? t("pipeline.stats.pages_html_size", "pages HTML · {{size}} Mo", {
                  size: totalSizeMb,
                })
              : t("pipeline.stats.pages_html", "pages HTML")
          }
        />
      )}
    </div>
  )
}
