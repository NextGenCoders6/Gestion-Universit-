// Tests de bout en bout du socle.
//
//   cd erp/frontend && npx playwright test
//
// La configuration démarre ses propres serveurs sur des ports à part
// (Django 8011 sur une base SQLite jetable, Vite 3011), sans toucher à ceux
// du travail quotidien (8000, 5173). La base est recréée et remplie par
// seed_demo à chaque lancement.
import { defineConfig, devices } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

process.env.E2E_DOSSIER ??= mkdtempSync(path.join(tmpdir(), 'erp-e2e-'));

const BACKEND = path.resolve(import.meta.dirname, '../backend');
const PYTHON = path.join(BACKEND, '.venv', 'bin', 'python');
const ENV_DJANGO = {
  DB_ENGINE: 'sqlite',
  DB_SQLITE_PATH: path.join(process.env.E2E_DOSSIER, 'e2e.sqlite3'),
  DEBUG: 'True',
  SECRET_KEY: 'cle-e2e-jetable',
  ALLOWED_HOSTS: '127.0.0.1,localhost',
  BASE_URL: 'http://127.0.0.1:8011',
};

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:3011',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `${PYTHON} manage.py migrate -v0 && ${PYTHON} manage.py seed_demo --reset && ${PYTHON} manage.py runserver 127.0.0.1:8011 --noreload`,
      cwd: BACKEND,
      env: ENV_DJANGO,
      url: 'http://127.0.0.1:8011/api/core/modules/',
      // /api/core/modules/ exige une connexion : 401 prouve que le serveur répond.
      ignoreHTTPSErrors: true,
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npx vite --port 3011 --strictPort --host 127.0.0.1',
      env: { ERP_API_URL: 'http://127.0.0.1:8011' },
      url: 'http://127.0.0.1:3011/login',
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
});
