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
  const [value, setValueState] = useState<TValue>(overrideValue ?? defaultValue)
  const allowedValuesKey = useMemo(
    () => allowedValues.join('\u0000'),
    [allowedValues],
  )
  const stableAllowedValues = useMemo(
    () => allowedValuesKey.split('\u0000') as TValue[],
    [allowedValuesKey],
  )

  useEffect(() => {
    if (!effectiveEnabled) {
      setValueState(defaultValue)
      return
    }

    if (overrideValue && stableAllowedValues.includes(overrideValue)) {
      setValueState(overrideValue)
      writeStoredProjectDesktopViewPreference(
        projectScope,
        key,
        overrideValue,
        stableAllowedValues,
        storage,
      )
      return
    }

    const storedValue = readStoredProjectDesktopViewPreference(
      projectScope,
      key,
      stableAllowedValues,
      storage,
    )
    setValueState(storedValue ?? defaultValue)
  }, [
    defaultValue,
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

      setValueState(nextValue)

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
    [effectiveEnabled, key, projectScope, stableAllowedValues, storage],
  )

  return [value, setValue] as const
}
