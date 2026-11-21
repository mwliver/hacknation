import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright – AED prototype: screenshots for the contest presentation and responsive/keyboard checks.
 * The AED API is mocked (e2e/aed/api-mocks.ts), so no backend is needed.
 *   npm run e2e:aed
 */
const PORT = 4300;

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  outputDir: './e2e/.results',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    locale: 'pl-PL',
    timezoneId: 'Europe/Warsaw',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npx ng serve --configuration dev --port ${PORT} --host 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}/pl`,
    timeout: 300_000,
    reuseExistingServer: true,
  },
});
