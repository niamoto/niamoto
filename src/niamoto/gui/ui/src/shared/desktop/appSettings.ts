import i18n, {
  getBestSupportedLanguage,
  type UiLanguage,
  type UiLanguagePreference,
} from '@/i18n'
import { invokeDesktop, isDesktopTauri } from '@/shared/desktop/tauri'

export interface AppSettings {
  auto_load_last_project: boolean
  ui_language: UiLanguagePreference
}

export const DEFAULT_APP_SETTINGS: AppSettings = {
  auto_load_last_project: true,
  ui_language: 'auto',
}

const UI_LANGUAGE_PREFERENCE_STORAGE_KEY = 'niamoto.uiLanguagePreference'

export function isTauriApp() {
  return isDesktopTauri()
}

export function normalizeUiLanguagePreference(
  value?: string | null
): UiLanguagePreference {
  if (value === 'fr' || value === 'en' || value === 'auto') {
    return value
  }

  return 'auto'
}

function readStoredUiLanguagePreference(): UiLanguagePreference {
  if (typeof window === 'undefined') {
    return 'auto'
  }

  return normalizeUiLanguagePreference(
    window.localStorage.getItem(UI_LANGUAGE_PREFERENCE_STORAGE_KEY)
  )
}

function writeStoredUiLanguagePreference(
  preference: UiLanguagePreference
): void {
  if (typeof window === 'undefined') {
    return
  }

  if (preference === 'auto') {
    window.localStorage.removeItem(UI_LANGUAGE_PREFERENCE_STORAGE_KEY)
    return
  }

  window.localStorage.setItem(UI_LANGUAGE_PREFERENCE_STORAGE_KEY, preference)
}

export async function getAppSettings(): Promise<AppSettings> {
  if (!isTauriApp()) {
    return {
      ...DEFAULT_APP_SETTINGS,
      ui_language: readStoredUiLanguagePreference(),
    }
  }

  const settings = await invokeDesktop<Partial<AppSettings>>('get_app_settings')

  return {
    ...DEFAULT_APP_SETTINGS,
    ...settings,
    ui_language: normalizeUiLanguagePreference(settings.ui_language),
  }
}

export async function setAppSettings(settings: AppSettings): Promise<void> {
  const nextSettings = {
    ...DEFAULT_APP_SETTINGS,
    ...settings,
    ui_language: normalizeUiLanguagePreference(settings.ui_language),
  }

  if (isTauriApp()) {
    await invokeDesktop('set_app_settings', {
      settings: nextSettings,
    })
  }

  writeStoredUiLanguagePreference(nextSettings.ui_language)
}

export async function applyUiLanguagePreference(
  preference: UiLanguagePreference
): Promise<UiLanguage> {
  const normalizedPreference = normalizeUiLanguagePreference(preference)
  const effectiveLanguage =
    normalizedPreference === 'auto'
      ? getBestSupportedLanguage()
      : normalizedPreference

  await i18n.changeLanguage(effectiveLanguage)

  return effectiveLanguage
}
