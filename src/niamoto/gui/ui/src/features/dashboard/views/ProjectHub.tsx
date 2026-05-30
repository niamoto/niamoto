import { StablePageSkeleton } from "@/components/loading/StableLoadingState"
import { getStableQueryState } from "@/components/loading/stableQueryState"
import { useDatasets } from "@/hooks/useDatasets"
import { useReferences } from "@/hooks/useReferences"
import { DashboardView } from "../components/DashboardView"
import { OnboardingView } from "../components/OnboardingView"

export default function ProjectHub() {
  const {
    data: datasetsData,
    isLoading: datasetsLoading,
    isFetching: datasetsFetching,
  } = useDatasets()
  const {
    data: referencesData,
    isLoading: referencesLoading,
    isFetching: referencesFetching,
  } = useReferences()

  const { isInitialLoading } = getStableQueryState({
    isLoading: datasetsLoading || referencesLoading,
    isFetching: datasetsFetching || referencesFetching,
    hasData: Boolean(datasetsData && referencesData),
  })

  if (isInitialLoading) {
    return <StablePageSkeleton />
  }

  const datasets = datasetsData?.datasets ?? []
  const references = referencesData?.references ?? []
  const hasData = datasets.length > 0 || references.length > 0

  if (!hasData) {
    return <OnboardingView />
  }

  return <DashboardView />
}
