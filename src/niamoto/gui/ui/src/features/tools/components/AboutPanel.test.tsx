import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { AboutPanel } from './AboutPanel'

const languageState = { value: 'en' }
const translations: Record<string, Record<string, string>> = {
  fr: {
    'settings.about': 'À propos',
    'settings.aboutDesc': 'Version de l’application, équipe et partenaires institutionnels',
    'settings.currentVersion': 'Version actuelle',
    'settings.checkUpdates': 'Vérifier les mises à jour',
    'settings.upToDate': 'À jour',
    'settings.updateAvailable': 'Version {{version}} disponible',
  },
  en: {
    'settings.about': 'About',
    'settings.aboutDesc': 'Application version, team, and institutional partners',
    'settings.currentVersion': 'Current version',
    'settings.checkUpdates': 'Check for updates',
    'settings.upToDate': 'Up to date',
    'settings.updateAvailable': 'Version {{version}} available',
  },
}

function interpolate(
  template: string,
  values?: Record<string, unknown>
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_match, key: string) =>
    String(values?.[key] ?? '')
  )
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValue?: string | Record<string, unknown>,
      options?: Record<string, unknown>
    ) => {
      const translated = translations[languageState.value]?.[key]
      if (translated) {
        return interpolate(translated, options)
      }

      if (typeof defaultValue === 'string') {
        return interpolate(defaultValue, options)
      }

      return key
    },
    i18n: {
      language: languageState.value,
      resolvedLanguage: languageState.value,
    },
  }),
}))

describe('AboutPanel', () => {
  it('renders the French institutional content inside the about card', () => {
    languageState.value = 'fr'

    const html = renderToStaticMarkup(
      <AboutPanel
        appVersion="1.2.3"
        status="idle"
        onCheckForUpdate={async () => {}}
        onInstallUpdate={async () => {}}
        onRestartApp={async () => {}}
      />
    )

    expect(html).toContain('Version de l’application, équipe et partenaires institutionnels')
    expect(html).toContain('Niamoteam')
    expect(html).toContain('Partenaires &amp; financeurs')
    expect(html).toContain('Julien Barbe')
    expect(html).toContain('Développeur')
    expect(html).toContain('Province Nord')
    expect(html).toContain('v1.2.3')
  })

  it('renders the English content and update state copy', () => {
    languageState.value = 'en'

    const html = renderToStaticMarkup(
      <AboutPanel
        appVersion="1.2.3"
        status="available"
        updateVersion="1.3.0"
        onCheckForUpdate={async () => {}}
        onInstallUpdate={async () => {}}
        onRestartApp={async () => {}}
      />
    )

    expect(html).toContain('Application version, team, and institutional partners')
    expect(html).toContain('Partners &amp; funders')
    expect(html).toContain('Developer')
    expect(html).toContain('Version 1.3.0 available')
    expect(html).toContain('Province Nord')
  })
})
