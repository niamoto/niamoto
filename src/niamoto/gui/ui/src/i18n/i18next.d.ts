// Type definitions for i18next
// Simplified to allow cross-namespace keys like 'common:actions.cancel'

import 'i18next';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    returnNull: false;
    // No strict resources typing to allow cross-namespace keys
  }
}
