/**
 * Hook to run pre-import impact checks after file upload.
 *
 * For each uploaded file, calls POST /api/imports/impact-check.
 * Returns matched reports (entity found) and unmatched file names.
 */

import { useState, useCallback } from 'react'
import { impactCheck, type ImpactCheckResult } from '../api/compatibility'

export interface CompatibilityCheckFailure {
  file: string
  error: string
}

interface CompatibilityCheckState {
  isChecking: boolean
  matched: ImpactCheckResult[]
  unmatched: string[]
  failed: CompatibilityCheckFailure[]
  error: string | null
}

export function useCompatibilityCheck() {
  const [state, setState] = useState<CompatibilityCheckState>({
    isChecking: false,
    matched: [],
    unmatched: [],
    failed: [],
    error: null,
  })

  const check = useCallback(async (files: Array<{ name: string; path: string }>) => {
    setState({ isChecking: true, matched: [], unmatched: [], failed: [], error: null })

    try {
      const results = await mapWithConcurrency(files, 2, async (f) => {
        try {
          const result = await impactCheck(f.path)
          return { file: f, result }
        } catch (err) {
          const message =
            err instanceof Error ? err.message : 'Compatibility check failed'
          return { file: f, result: null, error: message }
        }
      })

      const matched: ImpactCheckResult[] = []
      const unmatched: string[] = []
      const failed: CompatibilityCheckFailure[] = []

      for (const { file, result, error } of results) {
        if (error) {
          failed.push({ file: file.name, error })
        }
        if (result && result.entity_name) {
          matched.push(result)
        } else if (!error) {
          unmatched.push(file.name)
        }
      }

      const hasImpacts = matched.some(
        (r) =>
          r.impacts.length > 0 ||
          (r.widget_impacts?.length ?? 0) > 0 ||
          r.error ||
          r.skipped_reason ||
          r.info_message
      )
      const error =
        failed.length > 0
          ? `${failed.length} compatibility check${failed.length > 1 ? 's' : ''} failed`
          : null

      setState({
        isChecking: false,
        matched: hasImpacts ? matched : [],
        unmatched,
        failed,
        error,
      })

      return { matched: hasImpacts ? matched : [], unmatched, failed }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Compatibility checks failed'
      const failed = files.map((f) => ({ file: f.name, error: message }))
      setState({
        isChecking: false,
        matched: [],
        unmatched: [],
        failed,
        error: message,
      })
      return { matched: [], unmatched: [], failed }
    }
  }, [])

  const reset = useCallback(() => {
    setState({ isChecking: false, matched: [], unmatched: [], failed: [], error: null })
  }, [])

  return {
    ...state,
    check,
    reset,
  }
}

async function mapWithConcurrency<T, R>(
  items: T[],
  limit: number,
  mapper: (item: T) => Promise<R>,
): Promise<R[]> {
  const results: R[] = []
  let nextIndex = 0

  async function worker() {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex
      nextIndex += 1
      results[currentIndex] = await mapper(items[currentIndex])
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, () => worker()),
  )
  return results
}
