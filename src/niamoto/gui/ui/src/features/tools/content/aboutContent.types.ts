export type AboutLocale = 'fr' | 'en'

export interface AboutTeamMember {
  id: string
  name: string
  role: string
  url: string | null
}

export interface AboutOrganization {
  id: string
  name: string
  url: string | null
  logoAlt: string
  logoSrc: string
  categories: string[]
}

export interface AboutLocaleContent {
  summary: string
  teamTitle: string
  teamIntro: string
  members: AboutTeamMember[]
  partnersTitle: string
  partnersIntro: string
  organizations: AboutOrganization[]
}

export interface AboutContentBundle {
  generatedAt: string
  sourceShowcaseUrl: string
  locales: Record<AboutLocale, AboutLocaleContent>
}
