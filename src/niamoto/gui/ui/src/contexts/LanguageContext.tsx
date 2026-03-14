/**
 * LanguageContext - Centralized language management for multilingual content
 *
 * Provides:
 * - languages: Array of language codes configured for the site (e.g., ['fr', 'en'])
 * - defaultLang: The primary/default language code
 *
 * Usage:
 * 1. Wrap your app/panel with <LanguageProvider languages={[...]} defaultLang="fr">
 * 2. Use the useLanguages() hook in any component to access language settings
 *
 * This eliminates prop drilling for language settings across all form components.
 */

import { createContext, useContext, type ReactNode } from 'react'

interface LanguageContextValue {
  /** Available languages for content (e.g., ['fr', 'en']) */
  languages: string[]
  /** Default/primary language code */
  defaultLang: string
  /** Whether multilingual mode is active (more than one language) */
  isMultilingual: boolean
}

const defaultValue: LanguageContextValue = {
  languages: ['fr'],
  defaultLang: 'fr',
  isMultilingual: false,
}

const LanguageContext = createContext<LanguageContextValue>(defaultValue)

interface LanguageProviderProps {
  children: ReactNode
  /** Available languages for content */
  languages?: string[]
  /** Default/primary language */
  defaultLang?: string
}

/**
 * Provider component for language settings.
 * Wrap your site/panel with this to make language settings available everywhere.
 */
export function LanguageProvider({
  children,
  languages = ['fr'],
  defaultLang = 'fr',
}: LanguageProviderProps) {
  // Ensure defaultLang is in the languages array
  const effectiveLanguages = languages.includes(defaultLang)
    ? languages
    : [defaultLang, ...languages]

  const value: LanguageContextValue = {
    languages: effectiveLanguages,
    defaultLang,
    isMultilingual: effectiveLanguages.length > 1,
  }

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

/**
 * Hook to access language settings from any component.
 *
 * @example
 * const { languages, defaultLang, isMultilingual } = useLanguages()
 *
 * // Use in LocalizedInput
 * <LocalizedInput
 *   value={title}
 *   onChange={setTitle}
 *   // No need to pass languages/defaultLang - uses context!
 * />
 */
export function useLanguages(): LanguageContextValue {
  const context = useContext(LanguageContext)
  return context
}

export { LanguageContext }
export type { LanguageContextValue, LanguageProviderProps }
