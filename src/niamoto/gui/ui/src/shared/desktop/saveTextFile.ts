import { hasDesktopBridge, invokeDesktop } from './bridge'

export type NativeTextFileSaveResult =
  | { status: 'unavailable' }
  | { status: 'saved'; path?: string }
  | { status: 'cancelled' }

export interface NativeTextFileSaveRequest {
  filename: string
  contents: string
}

export async function saveTextFileWithNativeDialog({
  filename,
  contents,
}: NativeTextFileSaveRequest): Promise<NativeTextFileSaveResult> {
  if (!hasDesktopBridge()) {
    return { status: 'unavailable' }
  }

  const savedPath = await invokeDesktop<string | boolean | null>('save_text_file', {
    filename,
    contents,
  })

  if (typeof savedPath === 'string' && savedPath.trim()) {
    return { status: 'saved', path: savedPath }
  }

  if (savedPath === true) {
    return { status: 'saved' }
  }

  return { status: 'cancelled' }
}
