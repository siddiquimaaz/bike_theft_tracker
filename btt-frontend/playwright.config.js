import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig, devices } from '@playwright/test';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const venvPython =
  process.env.BTT_PYTHON?.trim() ||
  path.join(repoRoot, 'venv', isWin ? 'Scripts/python.exe' : 'bin/python');

const djangoCwd = path.join(repoRoot, 'btt-backend');

// BTT runs on 3001/8001 — ports 3000/8000 belong to MuseAI on this machine.
const DJANGO_PORT = process.env.BTT_DJANGO_PORT ?? '8001';
const VITE_PORT = process.env.BTT_VITE_PORT ?? '3001';

const djangoReadyUrl = `http://localhost:${DJANGO_PORT}/admin/login/`;
const viteReadyUrl = `http://localhost:${VITE_PORT}/`;

export default defineConfig({
  globalSetup: path.join(__dirname, 'playwright.global-setup.js'),

  testDir: '.',
  testMatch: ['e2e/**/*.spec.js', 'tests/e2e/**/*.spec.js'],

  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  workers: 1,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: viteReadyUrl,
    storageState: undefined,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      name: 'django-api',
      command: `"${venvPython}" manage.py runserver localhost:${DJANGO_PORT}`,
      cwd: djangoCwd,
      url: djangoReadyUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      name: 'vite-frontend',
      command: `npm run dev -- --host localhost --port ${VITE_PORT}`,
      cwd: __dirname,
      url: viteReadyUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
      dependencies: ['django-api'],
    },
  ],
});
