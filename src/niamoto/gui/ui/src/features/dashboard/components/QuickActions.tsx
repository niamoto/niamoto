import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Database, Eye, Layers, RefreshCw, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { FreshnessStatus } from "@/hooks/usePipelineStatus"

interface QuickActionProps {
  icon: React.ReactNode
  label: string
  description: string
  onClick: () => void
  disabled?: boolean
  variant?: "default" | "outline" | "primary"
}

function QuickAction({
  icon,
  label,
  description,
  onClick,
  disabled = false,
  variant = "outline",
}: QuickActionProps) {
  return (
    <Button
      variant={variant === "primary" ? "default" : "outline"}
      className={cn(
        "flex h-auto flex-col items-start gap-0.5 px-3 py-2.5 text-left",
        variant !== "primary" && "hover:bg-muted hover:text-foreground",
        disabled && "pointer-events-none opacity-40",
      )}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="flex items-center gap-1.5 text-xs font-semibold">
        {icon}
        {label}
      </span>
      <span className="text-[11px] font-normal text-muted-foreground">
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
}

export function QuickActions({
  dataStatus,
  groupsStatus,
  siteStatus,
  publicationStatus,
  isRunning,
}: QuickActionsProps) {
  const { t } = useTranslation("common")
  const navigate = useNavigate()

  const hasData = dataStatus === "fresh" || dataStatus === "stale"
  const groupsReady = groupsStatus === "fresh"
  const siteConfigured = siteStatus === "fresh"

  // Transform : dispo si on a des données et que les groupes ne sont pas en train de tourner
  const canTransform = hasData && !isRunning
  // Rebuild : dispo si groupes à jour et site configuré
  const canRebuild = groupsReady && siteConfigured && !isRunning
  // Publish : dispo si export stale ou jamais publié
  const canPublish =
    groupsReady &&
    (publicationStatus === "stale" || publicationStatus === "never_run") &&
    !isRunning

  return (
    <div className="flex flex-wrap gap-2">
      <QuickAction
        icon={<Database className="h-3.5 w-3.5" />}
        label={t("pipeline.action_import", "Import")}
        description={t("pipeline.action_import_desc", "Charger les données sources")}
        onClick={() => navigate("/sources/import")}
        disabled={isRunning}
        variant={dataStatus === "never_run" ? "primary" : "outline"}
      />
      <QuickAction
        icon={<Layers className="h-3.5 w-3.5" />}
        label={t("pipeline.action_recalculate", "Recalculer")}
        description={t(
          "pipeline.action_recalculate_desc",
          "Calculer les statistiques",
        )}
        onClick={() => navigate("/groups")}
        disabled={!canTransform}
        variant={
          groupsStatus === "stale" || groupsStatus === "never_run"
            ? "primary"
            : "outline"
        }
      />
      <QuickAction
        icon={<RefreshCw className="h-3.5 w-3.5" />}
        label={t("pipeline.action_rebuild", "Reconstruire")}
        description={t("pipeline.action_rebuild_desc", "Générer le site HTML")}
        onClick={() => navigate("/publish")}
        disabled={!canRebuild}
        variant={publicationStatus === "stale" ? "primary" : "outline"}
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
