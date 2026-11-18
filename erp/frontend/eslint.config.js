import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'playwright-report', 'test-results']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // `import * as React` des composants shadcn : inutile avec le JSX automatique, sans danger.
      'no-unused-vars': ['error', { varsIgnorePattern: '^(React|[A-Z_])' }],
    },
  },
  {
    // Composants shadcn et hôtes partagés : exportent aussi leurs variantes et utilitaires.
    files: ['src/components/ui/**/*.jsx', 'src/components/shared/**/*.jsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
  {
    files: ['src/**/*.test.{js,jsx}', 'src/test/**/*.js'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  {
    // Fichiers exécutés par Node (configuration, tests navigateur), pas par
    // le navigateur.
    files: ['*.config.js', 'e2e/**/*.js'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
])
