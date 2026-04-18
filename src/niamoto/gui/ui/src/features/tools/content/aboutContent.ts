import { aboutContent } from './aboutContent.generated'
import type { AboutLocale, AboutLocaleContent } from './aboutContent.types'

export { aboutContent }
export type {
  AboutContentBundle,
  AboutLocale,
  AboutLocaleContent,
  AboutOrganization,
  AboutTeamMember,
} from './aboutContent.types'

export function resolveAboutLocale(language: string): AboutLocale {
  return language.startsWith('fr') ? 'fr' : 'en'
}

export function getAboutContent(locale: AboutLocale): AboutLocaleContent {
  return aboutContent.locales[locale]
}
