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

const resources = {
  fr: {
    common: frCommon,
    import: frImport,
    transform: frTransform,
    export: frExport,
    visualize: frVisualize,
  },
  en: {
    common: enCommon,
    import: enImport,
    transform: enTransform,
    export: enExport,
    visualize: enVisualize,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    defaultNS: 'common',
    ns: ['common', 'import', 'transform', 'export', 'visualize'],
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
