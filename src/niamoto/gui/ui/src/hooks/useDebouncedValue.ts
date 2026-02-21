/**
 * Hook de debounce générique.
 * Retourne une valeur retardée de `delay` ms après le dernier changement.
 */
import { useState, useEffect } from 'react'

export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}
