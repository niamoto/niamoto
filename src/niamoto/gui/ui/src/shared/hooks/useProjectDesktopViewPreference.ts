import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  readStoredProjectDesktopViewPreference,
  writeStoredProjectDesktopViewPreference,
} from '@/shared/desktop/projectDesktopContext'
import { useCurrentProjectScope } from './useCurrentProjectScope'

interface UseProjectDesktopViewPreferenceOptions<TValue extends string> {
  key: string
  defaultValue: TValue
  allowedValues: readonly TValue[]
  enabled?: boolean
  desktopOnly?: boolean
  overrideValue?: TValue | null
  storage?: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
}

export function useProjectDesktopViewPreference<TValue extends string>({
  key,
  defaultValue,
  allowedValues,
  enabled = true,
  desktopOnly = true,
  overrideValue = null,
  storage,
}: UseProjectDesktopViewPreferenceOptions<TValue>) {
  const { desktopProjectScope, projectScope: fallbackAwareProjectScope } =
    useCurrentProjectScope()
  const projectScope = desktopOnly ? desktopProjectScope : fallbackAwareProjectScope
  const effectiveEnabled = enabled && Boolean(projectScope)
  const allowedValuesKey = useMemo(
    () => allowedValues.join('\u0000'),
    [allowedValues],
  )
  const stableAllowedValues = useMemo(
    () => allowedValuesKey.split('\u0000') as TValue[],
    [allowedValuesKey],
  )

  const preferenceCacheKey = [
    effectiveEnabled ? 'enabled' : 'disabled',
    projectScope ?? '',
    key,
    defaultValue,
    allowedValuesKey,
    overrideValue ?? '',
  ].join('\u0000')

  const resolvePreferenceValue = useCallback(() => {
    if (!effectiveEnabled) {
      return defaultValue
    }

    if (overrideValue && stableAllowedValues.includes(overrideValue)) {
      return overrideValue
    }

    const storedValue = readStoredProjectDesktopViewPreference(
      projectScope,
      key,
      stableAllowedValues,
      storage,
    )
    return storedValue ?? defaultValue
  }, [
    defaultValue,
    effectiveEnabled,
    key,
    overrideValue,
    projectScope,
    stableAllowedValues,
    storage,
  ])

  const [valueState, setValueState] = useState(() => ({
    cacheKey: preferenceCacheKey,
    value: resolvePreferenceValue(),
  }))
  const value = valueState.cacheKey === preferenceCacheKey
    ? valueState.value
    : resolvePreferenceValue()

  useEffect(() => {
    if (!effectiveEnabled || !overrideValue || !stableAllowedValues.includes(overrideValue)) {
      return
    }

    writeStoredProjectDesktopViewPreference(
      projectScope,
      key,
      overrideValue,
      stableAllowedValues,
      storage,
    )
  }, [
    effectiveEnabled,
    key,
    overrideValue,
    projectScope,
    stableAllowedValues,
    storage,
  ])

  const setValue = useCallback(
    (nextValue: TValue) => {
      if (!stableAllowedValues.includes(nextValue)) {
        return
      }

      setValueState({
        cacheKey: preferenceCacheKey,
        value: nextValue,
      })

      if (!effectiveEnabled) {
        return
      }

      writeStoredProjectDesktopViewPreference(
        projectScope,
        key,
        nextValue,
        stableAllowedValues,
        storage,
      )
    },
    [
      effectiveEnabled,
      key,
      preferenceCacheKey,
      projectScope,
      setValueState,
      stableAllowedValues,
      storage,
    ],
  )

  return [value, setValue] as const
}
