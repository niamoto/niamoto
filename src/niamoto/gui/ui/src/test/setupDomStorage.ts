function hasUsableLocalStorage(): boolean {
  if (typeof window === 'undefined') {
    return true
  }

  try {
    const storage = window.localStorage
    return typeof storage?.getItem === 'function'
      && typeof storage.setItem === 'function'
      && typeof storage.removeItem === 'function'
  } catch {
    return false
  }
}

function createMemoryStorage(): Storage {
  const entries = new Map<string, string>()

  return {
    get length() {
      return entries.size
    },
    clear() {
      entries.clear()
    },
    getItem(key: string) {
      return entries.get(key) ?? null
    },
    key(index: number) {
      return Array.from(entries.keys())[index] ?? null
    },
    removeItem(key: string) {
      entries.delete(key)
    },
    setItem(key: string, value: string) {
      entries.set(key, String(value))
    },
  }
}

if (!hasUsableLocalStorage()) {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: createMemoryStorage(),
  })
}
