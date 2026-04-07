import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import frCommon from './locales/fr/common.json';
import enCommon from './locales/en/common.json';
import frImport from './locales/fr/import.json';
import enImport from './locales/en/import.json';
import frTransform from './locales/fr/transform.json';
import enTransform from './locales/en/transform.json';
import frExport from './locales/fr/export.json';
import enExport from './locales/en/export.json';
import frVisualize from './locales/fr/visualize.json';
import enVisualize from './locales/en/visualize.json';
import frSite from './locales/fr/site.json';
import enSite from './locales/en/site.json';
import frWidgets from './locales/fr/widgets.json';
import enWidgets from './locales/en/widgets.json';
import frSources from './locales/fr/sources.json';
import enSources from './locales/en/sources.json';
import frIndexConfig from './locales/fr/indexConfig.json';
import enIndexConfig from './locales/en/indexConfig.json';
import frTools from './locales/fr/tools.json';
import enTools from './locales/en/tools.json';
import frPublish from './locales/fr/publish.json';
import enPublish from './locales/en/publish.json';
import frFeedback from './locales/fr/feedback.json';
import enFeedback from './locales/en/feedback.json';

export const SUPPORTED_UI_LANGUAGES = ['fr', 'en'] as const;

export type UiLanguage = (typeof SUPPORTED_UI_LANGUAGES)[number];
export type UiLanguagePreference = UiLanguage | 'auto';

export function normalizeUiLanguage(value?: string | null): UiLanguage {
  const normalized = value?.toLowerCase();

  if (normalized?.startsWith('fr')) {
    return 'fr';
  }

  if (normalized?.startsWith('en')) {
    return 'en';
  }

  return 'en';
}

export function getBestSupportedLanguage(
  candidates?: readonly string[] | string | null
): UiLanguage {
  const rawCandidates = Array.isArray(candidates)
    ? candidates
    : candidates
      ? [candidates]
      : typeof navigator !== 'undefined'
        ? [...navigator.languages, navigator.language]
        : [];

  for (const candidate of rawCandidates) {
    const normalized = candidate?.toLowerCase();

    if (normalized?.startsWith('fr')) {
      return 'fr';
    }

    if (normalized?.startsWith('en')) {
      return 'en';
    }
  }

  return 'en';
}

const resources = {
  fr: {
    common: frCommon,
    import: frImport,
    transform: frTransform,
    export: frExport,
    visualize: frVisualize,
    site: frSite,
    widgets: frWidgets,
    sources: frSources,
    indexConfig: frIndexConfig,
    tools: frTools,
    publish: frPublish,
    feedback: frFeedback,
  },
  en: {
    common: enCommon,
    import: enImport,
    transform: enTransform,
    export: enExport,
    visualize: enVisualize,
    site: enSite,
    widgets: enWidgets,
    sources: enSources,
    indexConfig: enIndexConfig,
    tools: enTools,
    publish: enPublish,
    feedback: enFeedback,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    defaultNS: 'common',
    ns: ['common', 'import', 'transform', 'export', 'visualize', 'site', 'widgets', 'sources', 'indexConfig', 'tools', 'publish', 'feedback'],
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_UI_LANGUAGES,
    load: 'languageOnly',
    debug: false,

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    detection: {
      order: ['navigator'],
      caches: [],
    },
  });

export default i18n;
