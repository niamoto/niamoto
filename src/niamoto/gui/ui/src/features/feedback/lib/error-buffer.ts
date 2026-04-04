import type { ErrorEntry } from '../types'

const BUFFER_SIZE = 10
const buffer: ErrorEntry[] = []

export function initErrorBuffer(): void {
  const originalError = console.error
  console.error = (...args: unknown[]) => {
    pushEntry(args.map(String).join(' '))
    originalError.apply(console, args)
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
      pushEntry(
        event.reason?.message || String(event.reason),
        event.reason?.stack
      )
    })
  }
}

function pushEntry(message: string, stack?: string): void {
  if (buffer.length >= BUFFER_SIZE) buffer.shift()
  buffer.push({ message, stack, timestamp: new Date().toISOString() })
}

export function getRecentErrors(): ErrorEntry[] {
  return [...buffer]
}
