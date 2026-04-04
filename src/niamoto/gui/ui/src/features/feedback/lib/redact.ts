/**
 * Redact sensitive information (local paths, usernames) from strings before
 * displaying to the user or sending to the Worker.
 */
export function redact(text: string): string {
  return text
    // macOS: /Users/<username>/... → <user>/...
    .replace(/\/Users\/[^/]+\//g, '<user>/')
    // Linux: /home/<username>/... → <user>/...
    .replace(/\/home\/[^/]+\//g, '<user>/')
    // Windows: C:\Users\<username>\... → <user>\...
    .replace(/[A-Z]:\\Users\\[^\\]+\\/gi, '<user>\\')
    // Home dir tilde expansion
    .replace(/~\/[^/\s]+/g, '<home>')
}

export function redactObject<T>(obj: T): T {
  if (typeof obj === 'string') return redact(obj) as T
  if (Array.isArray(obj)) return obj.map(redactObject) as T
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [k, redactObject(v)])
    ) as T
  }
  return obj
}
