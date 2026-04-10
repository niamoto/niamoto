import { createContext } from 'react'

export interface LanguageContextValue {
  languages: string[]
  defaultLang: string
  isMultilingual: boolean
}

export const defaultLanguageContextValue: LanguageContextValue = {
  languages: ['fr'],
  defaultLang: 'fr',
  isMultilingual: false,
}

export const LanguageContext = createContext<LanguageContextValue>(
  defaultLanguageContextValue
)
