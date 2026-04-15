import { useLanguages } from '@/shared/contexts/useLanguages'

export type LocalizedString = string | Record<string, string>

export function resolveLocalizedString(
  value: LocalizedString | undefined,
  lang: string,
  fallbackLang = 'fr'
): string {
  if (value === undefined || value === null) return ''
  if (typeof value === 'string') return value
  return value[lang] || value[fallbackLang] || Object.values(value)[0] || ''
}

export function useLocalizedString(
  value: LocalizedString | undefined,
  defaultLangProp?: string
) {
  const languageContext = useLanguages()
  const defaultLang = defaultLangProp ?? languageContext.defaultLang

  const isLocalized = typeof value === 'object' && value !== null

  const resolve = (lang?: string): string => {
    const targetLang = lang || defaultLang
    return resolveLocalizedString(value, targetLang, defaultLang)
  }

  const getAllTranslations = (): Record<string, string> => {
    if (typeof value === 'string') {
      return { [defaultLang]: value }
    }
    if (typeof value === 'object' && value !== null) {
      return value
    }
    return {}
  }

  return {
    isLocalized,
    resolve,
    getAllTranslations,
    raw: value,
  }
}
