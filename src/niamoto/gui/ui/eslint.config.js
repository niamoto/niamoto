import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { globalIgnores } from 'eslint/config'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-empty-object-type': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-hooks/static-components': 'warn',
      'react-hooks/purity': 'warn',
      'react-hooks/immutability': 'warn',
      'react-refresh/only-export-components': 'warn',
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@/features/dashboard',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
            {
              name: '@/features/import',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
            {
              name: '@/features/tools',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
            {
              name: '@/features/publish',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
            {
              name: '@/features/collections',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
            {
              name: '@/features/site',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
            {
              name: '@/features/welcome',
              message: 'Import leaf modules directly to preserve route chunk boundaries.',
            },
          ],
        },
      ],
    },
  },
  {
    files: ['src/features/import/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@/hooks/useDatasets',
              message: 'Import datasets hooks from "@/features/import/hooks/useDatasets".',
            },
            {
              name: '@/hooks/useReferences',
              message: 'Import reference hooks from "@/features/import/hooks/useReferences".',
            },
            {
              name: '@/hooks/useImportSummary',
              message: 'Import summary hooks from "@/features/import/hooks/useImportSummary".',
            },
            {
              name: '@/hooks/useImportSummaryDetailed',
              message:
                'Import detailed summary hooks from "@/features/import/hooks/useImportSummaryDetailed".',
            },
          ],
        },
      ],
    },
  },
  {
    files: ['src/features/publish/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@/lib/api/export',
              message: 'Import publish export APIs from "@/features/publish/api/export".',
            },
          ],
        },
      ],
    },
  },
  {
    files: [
      'src/components/ui/badge.tsx',
      'src/components/ui/button.tsx',
      'src/components/ui/toggle.tsx',
      'src/features/import/components/enrichment/enrichmentRenderers.tsx',
      'src/features/publish/views/deployPlatformConfig.tsx',
      'src/features/welcome/views/index.tsx',
    ],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
