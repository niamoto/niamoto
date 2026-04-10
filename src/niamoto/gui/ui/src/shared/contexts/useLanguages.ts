import { useContext } from 'react'

import { LanguageContext, type LanguageContextValue } from './languageContext'

export function useLanguages(): LanguageContextValue {
  return useContext(LanguageContext)
}
