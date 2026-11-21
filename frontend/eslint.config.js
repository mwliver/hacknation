import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'coverage/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      globals: {
        AbortController: 'readonly',
        AbortSignal: 'readonly',
        console: 'readonly',
        CustomEvent: 'readonly',
        document: 'readonly',
        Element: 'readonly',
        Event: 'readonly',
        fetch: 'readonly',
        FormData: 'readonly',
        globalThis: 'readonly',
        HTMLElement: 'readonly',
        HTMLInputElement: 'readonly',
        localStorage: 'readonly',
        location: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        window: 'readonly',
      },
    },
  },
);
