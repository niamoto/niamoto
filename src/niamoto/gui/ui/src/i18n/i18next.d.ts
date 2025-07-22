import 'i18next';
import type common from './locales/fr/common.json';
import type importNs from './locales/fr/import.json';
import type transform from './locales/fr/transform.json';
import type exportNs from './locales/fr/export.json';
import type visualize from './locales/fr/visualize.json';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof common;
      import: typeof importNs;
      transform: typeof transform;
      export: typeof exportNs;
      visualize: typeof visualize;
    };
  }
}
