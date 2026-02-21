/**
 * Cache LRU générique pour stocker les previews HTML.
 * Éviction automatique du plus ancien quand la taille max est atteinte.
 */
export class LRUCache<T> {
  private cache = new Map<string, T>()

  constructor(private maxSize: number = 64) {}

  get(key: string): T | undefined {
    const value = this.cache.get(key)
    if (value === undefined) return undefined
    // Promouvoir en fin de Map (plus récent)
    this.cache.delete(key)
    this.cache.set(key, value)
    return value
  }

  set(key: string, value: T): void {
    // Si la clé existe déjà, la supprimer d'abord pour la promouvoir
    if (this.cache.has(key)) {
      this.cache.delete(key)
    } else if (this.cache.size >= this.maxSize) {
      // Évicter le plus ancien (premier élément de la Map)
      const oldestKey = this.cache.keys().next().value
      if (oldestKey !== undefined) {
        this.cache.delete(oldestKey)
      }
    }
    this.cache.set(key, value)
  }

  has(key: string): boolean {
    return this.cache.has(key)
  }

  clear(): void {
    this.cache.clear()
  }

  get size(): number {
    return this.cache.size
  }
}

/** Cache global des previews HTML (max 64 entrées, ~6MB max) */
export const previewHtmlCache = new LRUCache<string>(64)
