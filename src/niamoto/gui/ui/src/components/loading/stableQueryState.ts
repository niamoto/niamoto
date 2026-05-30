interface StableQueryStateInput {
  isLoading?: boolean
  isFetching?: boolean
  hasData?: boolean
}

export function getStableQueryState({
  isLoading = false,
  isFetching = false,
  hasData = false,
}: StableQueryStateInput) {
  const isInitialLoading = isLoading && !hasData

  return {
    isInitialLoading,
    isRefreshing: isFetching && !isInitialLoading,
  }
}
