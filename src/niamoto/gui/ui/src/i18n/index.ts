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
    fallbackLng: 'fr',
    debug: false,

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;
