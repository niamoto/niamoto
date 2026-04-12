import { Loader2 } from "lucide-react"

import { useDatasets } from "@/hooks/useDatasets"
import { useReferences } from "@/hooks/useReferences"
import { DashboardView } from "../components/DashboardView"
import { OnboardingView } from "../components/OnboardingView"

export default function ProjectHub() {
  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets()
  const { data: referencesData, isLoading: referencesLoading } = useReferences()

  const isInitialLoading =
    (datasetsLoading && !datasetsData) ||
    (referencesLoading && !referencesData)

  if (isInitialLoading) {
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
