import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Database, Eye, Layers, Map, RefreshCw, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { FreshnessStatus } from "@/hooks/usePipelineStatus"

interface QuickActionProps {
  icon: React.ReactNode
  label: string
  description: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
}

function QuickAction({
  icon,
  label,
  description,
  onClick,
  disabled = false,
  primary = false,
}: QuickActionProps) {
  return (
    <Button
      variant={primary ? "default" : "outline"}
      className={cn(
        "flex h-auto flex-col items-start gap-0.5 px-3 py-2.5 text-left",
        !primary && "hover:bg-muted hover:text-foreground",
        disabled && "pointer-events-none opacity-40",
      )}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="flex items-center gap-1.5 text-xs font-semibold">
        {icon}
        {label}
      </span>
      <span
        className={cn(
          "text-[11px] font-normal",
          primary ? "text-primary-foreground/60" : "text-muted-foreground",
        )}
      >
        {description}
      </span>
    </Button>
  )
}

interface QuickActionsProps {
  dataStatus: FreshnessStatus
  groupsStatus: FreshnessStatus
  siteStatus: FreshnessStatus
  publicationStatus: FreshnessStatus
  isRunning: boolean
  /** True si la DB contient des entités (indépendamment du job store GUI). */
  hasEntities: boolean
}

export function QuickActions({
  dataStatus,
  groupsStatus,
  siteStatus,
  publicationStatus,
  isRunning,
  hasEntities,
}: QuickActionsProps) {
  const { t } = useTranslation("common")
  const navigate = useNavigate()

  // hasData : données présentes, qu'elles viennent du GUI ou du CLI
  const hasData =
    hasEntities ||
    dataStatus === "fresh" ||
    dataStatus === "stale"

  const groupsReady = groupsStatus === "fresh"
  const siteConfigured = siteStatus === "fresh"

  const canTransform = hasData && !isRunning
  const canRebuild = groupsReady && siteConfigured && !isRunning
  const canPublish = siteConfigured && publicationStatus === "fresh" && !isRunning

  const recalcPrimary =
    hasData &&
    !isRunning &&
    (groupsStatus === "stale" || groupsStatus === "never_run")

  const rebuildPrimary =
    canRebuild &&
    (publicationStatus === "stale" || publicationStatus === "never_run")

  return (
    <div className="flex flex-wrap gap-2">
      <QuickAction
        icon={<Database className="h-3.5 w-3.5" />}
        label={t("pipeline.action_import", "Import")}
        description={t("pipeline.action_import_desc", "Charger les données sources")}
        onClick={() => navigate("/sources/import")}
        disabled={isRunning}
      />
      <QuickAction
        icon={<Layers className="h-3.5 w-3.5" />}
        label={t("pipeline.action_recalculate", "Recalculer")}
        description={t("pipeline.action_recalculate_desc", "Calculer les statistiques")}
        onClick={() => navigate("/groups")}
        disabled={!canTransform}
        primary={recalcPrimary}
      />
      <QuickAction
        icon={<Map className="h-3.5 w-3.5" />}
        label={t("pipeline.action_configure", "Configurer")}
        description={t("pipeline.action_configure_desc", "Définir les pages du site")}
        onClick={() => navigate("/site/pages")}
        disabled={isRunning}
      />
      <QuickAction
        icon={<RefreshCw className="h-3.5 w-3.5" />}
        label={t("pipeline.action_rebuild", "Reconstruire")}
        description={t("pipeline.action_rebuild_desc", "Générer le site HTML")}
        onClick={() => navigate("/publish")}
        disabled={!canRebuild}
        primary={rebuildPrimary}
      />
      <QuickAction
        icon={<Eye className="h-3.5 w-3.5" />}
        label={t("tools.preview", "Prévisualiser")}
        description={t("pipeline.action_preview_desc", "Voir le rendu des widgets")}
        onClick={() => navigate("/tools/preview")}
        disabled={!hasData}
      />
      <QuickAction
        icon={<Send className="h-3.5 w-3.5" />}
        label={t("pipeline.action_publish", "Publier")}
        description={t("pipeline.action_publish_desc", "Déployer sur le serveur")}
        onClick={() => navigate("/publish?panel=destinations")}
        disabled={!canPublish}
      />
    </div>
  )
}
