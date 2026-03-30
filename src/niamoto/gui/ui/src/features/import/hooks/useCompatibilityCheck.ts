/**
 * Hook to run pre-import impact checks after file upload.
 *
 * For each uploaded file, calls POST /api/imports/impact-check.
 * Returns matched reports (entity found) and unmatched file names.
 */

import { useState, useCallback } from 'react'
import { impactCheck, type ImpactCheckResult } from '../api/compatibility'

interface CompatibilityCheckState {
  isChecking: boolean
  matched: ImpactCheckResult[]
  unmatched: string[]
  error: string | null
}

export function useCompatibilityCheck() {
  const [state, setState] = useState<CompatibilityCheckState>({
    isChecking: false,
    matched: [],
    unmatched: [],
    error: null,
  })

  const check = useCallback(async (files: Array<{ name: string; path: string }>) => {
    setState({ isChecking: true, matched: [], unmatched: [], error: null })

    try {
      const results = await Promise.all(
        files.map(async (f) => {
          try {
            const result = await impactCheck(f.path)
            return { file: f, result }
          } catch {
            // Non-blocking: if the API fails, treat as unmatched
            return { file: f, result: null }
          }
        })
      )

      const matched: ImpactCheckResult[] = []
      const unmatched: string[] = []

      for (const { file, result } of results) {
        if (result && result.entity_name) {
          matched.push(result)
        } else {
          unmatched.push(file.name)
        }
      }

      const hasImpacts = matched.some(
        (r) => r.impacts.length > 0 || r.error || r.skipped_reason || r.info_message
      )

      setState({
        isChecking: false,
        matched: hasImpacts ? matched : [],
        unmatched,
        error: null,
      })

      return { matched: hasImpacts ? matched : [], unmatched }
    } catch (err: any) {
      // Non-blocking: if everything fails, skip the check
      setState({
        isChecking: false,
        matched: [],
        unmatched: files.map((f) => f.name),
        error: null,
      })
      return { matched: [], unmatched: files.map((f) => f.name) }
    }
  }, [])

  const reset = useCallback(() => {
    setState({ isChecking: false, matched: [], unmatched: [], error: null })
  }, [])

  return {
    ...state,
    check,
    reset,
  }
}
