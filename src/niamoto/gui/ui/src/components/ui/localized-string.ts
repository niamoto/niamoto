import { useLanguages } from '@/shared/contexts/useLanguages'

export type LocalizedString = string | Record<string, string>

export function useLocalizedString(
  value: LocalizedString | undefined,
  defaultLangProp?: string
) {
  const languageContext = useLanguages()
  const defaultLang = defaultLangProp ?? languageContext.defaultLang

  const isLocalized = typeof value === 'object' && value !== null

  const resolve = (lang?: string): string => {
    if (value === undefined || value === null) return ''
    if (typeof value === 'string') return value
    const targetLang = lang || defaultLang
    return value[targetLang] || value[defaultLang] || Object.values(value)[0] || ''
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
