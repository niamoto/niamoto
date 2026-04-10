import { useContext } from 'react'

import { LanguageContext, type LanguageContextValue } from './language-context'

export function useLanguages(): LanguageContextValue {
  return useContext(LanguageContext)
}
